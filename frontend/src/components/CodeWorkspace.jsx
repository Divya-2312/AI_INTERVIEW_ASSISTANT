import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Code2,
  RotateCcw,
  FlaskConical,
  CheckCircle2,
  XCircle,
  Wrench,
  Database,
  AlertTriangle,
  Clock,
} from "lucide-react";
import { SolutionViewer } from "./SolutionViewer";

const SECTION_LABELS = ["Input:", "Output:", "Constraints:", "Example:"];

function parseProblemStatement(text) {
  if (!text) return { statement: "", sections: [] };

  const pattern = new RegExp(
    `(${SECTION_LABELS.map((l) => l.replace(":", "\\:")).join("|")})`,
    "g"
  );

  const parts = text
    .split(pattern)
    .map((p) => p.trim())
    .filter(Boolean);

  let statement = "";
  const sections = [];
  let i = 0;

  if (parts.length && !SECTION_LABELS.includes(parts[0])) {
    statement = parts[0];
    i = 1;
  }

  for (; i < parts.length; i += 2) {
    const label = parts[i];
    const body = parts[i + 1] || "";
    if (SECTION_LABELS.includes(label)) {
      sections.push({ label: label.replace(":", ""), body });
    }
  }

  if (!sections.length) return { statement: text, sections: [] };

  return { statement, sections };
}

/**
 * Parses one or more `CREATE TABLE name (...);` statements into a
 * structured form: [{ name, columns: [{ name, type, constraint }] }].
 * Splits columns on commas that are OUTSIDE parentheses, so types like
 * DECIMAL(10,2) or VARCHAR(255) don't get split in half. Lines that are
 * table-level constraints (PRIMARY KEY (...), FOREIGN KEY (...), etc.)
 * rather than a real column are kept separately and shown underneath the
 * table instead of as a fake row.
 */
function parseSchemaToTables(schemaText) {
  if (!schemaText) return [];

  const tables = [];
  const tableRegex = /CREATE TABLE\s+(\w+)\s*\(([\s\S]*?)\)\s*;/gi;
  let match;

  while ((match = tableRegex.exec(schemaText)) !== null) {
    const tableName = match[1];
    const body = match[2];

    // Split on top-level commas only (depth 0), so "DECIMAL(10,2)" stays intact.
    const rawColumns = [];
    let depth = 0;
    let current = "";
    for (const ch of body) {
      if (ch === "(") depth++;
      if (ch === ")") depth--;
      if (ch === "," && depth === 0) {
        rawColumns.push(current.trim());
        current = "";
      } else {
        current += ch;
      }
    }
    if (current.trim()) rawColumns.push(current.trim());

    const columns = [];
    const tableConstraints = [];

    rawColumns.forEach((line) => {
      if (/^(PRIMARY KEY|FOREIGN KEY|UNIQUE|CHECK|CONSTRAINT)\b/i.test(line)) {
        tableConstraints.push(line);
        return;
      }
      const parts = line.split(/\s+/);
      const colName = parts[0];
      const rest = parts.slice(1).join(" ");
      const typeMatch = rest.match(/^([A-Za-z]+(?:\([^)]*\))?)/);
      const type = typeMatch ? typeMatch[1] : rest;
      const constraint = rest.slice(type.length).trim();
      columns.push({ name: colName, type, constraint });
    });

    tables.push({ name: tableName, columns, tableConstraints });
  }

  return tables;
}

const DIFFICULTY_COLORS = {
  easy: { color: "#15803d", bg: "#dcfce7" },
  medium: { color: "#92400e", bg: "#fef3c7" },
  hard: { color: "#b91c1c", bg: "#fee2e2" },
};

const CodeEditor = ({ value, onChange, disabled }) => {
  const gutterRef = useRef(null);
  const textareaRef = useRef(null);
  const [blockedNotice, setBlockedNotice] = useState(false);
  const noticeTimer = useRef(null);

  // Solutions must be typed by hand: block copy, cut, paste, drag-and-drop and the
  // context menu on the editor, plus any input the browser reports as a paste/drop
  // (covers Ctrl/Cmd+V, Shift+Insert, right-click paste, Edit menu, middle-click and
  // mobile long-press paste). Native listeners are used so every route is caught.
  // This is a client-side restriction: it stops the normal editor interface, not
  // someone tampering with the page itself.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return undefined;

    const block = (e) => {
      e.preventDefault();
      setBlockedNotice(true);
      clearTimeout(noticeTimer.current);
      noticeTimer.current = setTimeout(() => setBlockedNotice(false), 3000);
    };
    const BLOCKED_INPUT_TYPES = new Set([
      "insertFromPaste",
      "insertFromPasteAsQuotation",
      "insertFromDrop",
      "insertFromYank",
      "deleteByCut",
    ]);
    const onBeforeInput = (e) => {
      if (BLOCKED_INPUT_TYPES.has(e.inputType)) block(e);
    };

    const events = ["paste", "copy", "cut", "drop", "dragstart", "contextmenu"];
    events.forEach((name) => el.addEventListener(name, block));
    el.addEventListener("beforeinput", onBeforeInput);
    return () => {
      events.forEach((name) => el.removeEventListener(name, block));
      el.removeEventListener("beforeinput", onBeforeInput);
      clearTimeout(noticeTimer.current);
    };
  }, []);

  const lineCount = Math.max(1, value.split("\n").length);

  const syncScroll = () => {
    if (gutterRef.current && textareaRef.current) {
      gutterRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Tab") {
      e.preventDefault();
      const el = textareaRef.current;
      const start = el.selectionStart;
      const end = el.selectionEnd;
      const next = value.slice(0, start) + "    " + value.slice(end);
      onChange(next);

      requestAnimationFrame(() => {
        el.selectionStart = el.selectionEnd = start + 4;
      });
    }
  };

  return (
    <>
    <div className="code-editor-shell">
      <div className="code-editor-gutter" ref={gutterRef}>
        {Array.from({ length: lineCount }, (_, i) => (
          <div key={i} className="code-editor-lineno">
            {i + 1}
          </div>
        ))}
      </div>

      <textarea
        ref={textareaRef}
        className="code-editor-textarea"
        value={value}
        disabled={disabled}
        spellCheck={false}
        onScroll={syncScroll}
        onKeyDown={handleKeyDown}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
    {blockedNotice && (
      <div className="cj-note" role="status">
        Copy and paste are disabled in the editor. Please type your solution.
      </div>
    )}
    </>
  );
};

export { SolutionViewer };

/* Solution is only revealed when the candidate explicitly asks for it. */
export const SolutionReveal = ({
  children,
  interviewId,
  format = "coding",
  language = "java",
  questionKey,
  preloadedSolution = null,
}) => {
  if (interviewId || preloadedSolution) {
    return (
      <SolutionViewer
        interviewId={interviewId}
        format={format}
        language={language}
        questionKey={questionKey}
        preloadedSolution={preloadedSolution}
      />
    );
  }

  const [shown, setShown] = useState(false);
  return (
    <div className="judge-solution">
      <button
        type="button"
        className="cj-reset-btn"
        onClick={() => setShown((v) => !v)}
        aria-expanded={shown}
      >
        Solution
      </button>
      {shown && children}
    </div>
  );
};

export const ScoreBreakdown = ({ evaluation }) => {
  if (!evaluation) return null;

  // Coding format must NOT show theory chips (Relevance, Correctness, Concept Coverage, Communication)
  if (
    evaluation.questionFormat === "coding" ||
    evaluation.format === "coding" ||
    evaluation.judgeMode ||
    (evaluation.testCaseResults && evaluation.testCaseResults.length > 0)
  ) {
    return null;
  }

  const pct = (v) =>
    typeof v === "number" ? Math.round(v * 100) : null;

  const items = [
    { label: "Relevance", value: pct(evaluation.relevance) },
    { label: "Correctness", value: pct(evaluation.correctness) },
    typeof evaluation.accuracy === "number"
      ? { label: "Accuracy", value: pct(evaluation.accuracy) }
      : { label: "Concept Coverage", value: pct(evaluation.conceptCoverage) },
    { label: "Communication", value: pct(evaluation.communication) },
  ].filter((i) => i.value !== null);

  if (!items.length) return null;

  return (
    <div className="score-breakdown">
      {items.map((i) => (
        <span key={i.label} className="score-breakdown-chip">
          {i.label}: <strong>{i.value}%</strong>
        </span>
      ))}
    </div>
  );
};

/* ---------------- Schema Table ---------------- */

const schemaTableStyles = {
  wrap: { marginBottom: "1rem" },
  name: {
    fontFamily: "monospace",
    fontWeight: 700,
    fontSize: "0.85rem",
    color: "#3730a3",
    backgroundColor: "#eef2ff",
    padding: "0.3rem 0.6rem",
    borderRadius: "6px 6px 0 0",
    display: "inline-block",
    borderBottom: "2px solid #6366f1",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "0.82rem",
    marginTop: "0",
  },
  th: {
    textAlign: "left",
    padding: "0.4rem 0.6rem",
    backgroundColor: "#f8fafc",
    borderBottom: "1px solid #e2e8f0",
    color: "#64748b",
    fontWeight: 600,
    fontSize: "0.72rem",
    textTransform: "uppercase",
    letterSpacing: "0.03em",
  },
  td: {
    padding: "0.4rem 0.6rem",
    borderBottom: "1px solid #f1f5f9",
    fontFamily: "monospace",
  },
  tdName: { fontWeight: 600, color: "#1e293b" },
  tdType: { color: "#7c3aed" },
  tdConstraint: { color: "#dc2626", fontSize: "0.78rem" },
  constraintsBox: {
    fontSize: "0.78rem",
    color: "#64748b",
    fontFamily: "monospace",
    padding: "0.35rem 0.6rem",
    backgroundColor: "#f8fafc",
    borderTop: "1px dashed #e2e8f0",
  },
};

const SchemaTable = ({ table }) => (
  <div style={schemaTableStyles.wrap}>
    <span style={schemaTableStyles.name}>{table.name}</span>
    <table style={schemaTableStyles.table}>
      <thead>
        <tr>
          <th style={schemaTableStyles.th}>Column</th>
          <th style={schemaTableStyles.th}>Type</th>
          <th style={schemaTableStyles.th}>Constraint</th>
        </tr>
      </thead>
      <tbody>
        {table.columns.map((col, i) => (
          <tr key={i}>
            <td style={{ ...schemaTableStyles.td, ...schemaTableStyles.tdName }}>{col.name}</td>
            <td style={{ ...schemaTableStyles.td, ...schemaTableStyles.tdType }}>{col.type}</td>
            <td style={{ ...schemaTableStyles.td, ...schemaTableStyles.tdConstraint }}>
              {col.constraint || "\u2014"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
    {table.tableConstraints.length > 0 && (
      <div style={schemaTableStyles.constraintsBox}>
        {table.tableConstraints.map((c, i) => (
          <div key={i}>{c}</div>
        ))}
      </div>
    )}
  </div>
);

/* ---------------- Code Workspace ---------------- */

export const CodeWorkspace = ({
  question,
  value,
  onChange,
  onReset,
  disabled,
  interviewId,
  isSubmitted = false,
}) => {
  const parsed = useMemo(
    () => parseProblemStatement(question.questionText),
    [question.questionText]
  );

  const schemaTables = useMemo(
    () => parseSchemaToTables(question.schema),
    [question.schema]
  );

  const diffKey = (question.difficulty || "medium").toLowerCase();
  const diffStyle =
    DIFFICULTY_COLORS[diffKey] || DIFFICULTY_COLORS.medium;

  const editorValue =
    value && value.length > 0 ? value : question.starterCode || "";

  const isSql = (question.language || "java").toLowerCase() === "sql";

  return (
    <div className="code-judge">
      <div className="code-judge-left">
        <div className="code-judge-left-header">
          <span className="code-judge-title">
            {question.title || "Coding Problem"}
          </span>

          <div className="code-judge-badges">
            <span
              className="cj-badge"
              style={{
                color: diffStyle.color,
                backgroundColor: diffStyle.bg,
              }}
            >
              {diffKey.charAt(0).toUpperCase() + diffKey.slice(1)}
            </span>

            {question.category && (
              <span className="cj-badge cj-badge-neutral">
                {question.category}
              </span>
            )}
          </div>
        </div>

        <div className="code-judge-scroll">
          {parsed.statement && (
            <p className="cj-statement">{parsed.statement}</p>
          )}

          {/* Schema, rendered as real column/type tables (parsed from the
              CREATE TABLE DDL) instead of a raw SQL text block -- only
              relevant for SQL questions. Falls back to nothing if parsing
              finds no tables (e.g. unexpected DDL formatting), so a
              parsing miss never hides the section entirely without a
              trace; consider also showing the raw schema pre-block in
              that fallback case if it happens often. */}
          {isSql && schemaTables.length > 0 && (
            <div className="cj-section">
              <div className="cj-section-label">
                <Database size={13} style={{ marginRight: "0.3rem", verticalAlign: "-2px" }} />
                Schema
              </div>
              {schemaTables.map((table, i) => (
                <SchemaTable key={i} table={table} />
              ))}
            </div>
          )}

          {isSql && question.sampleData && (
            <div className="cj-section">
              <div className="cj-section-label">Sample Data</div>
              <pre className="cj-schema-block">
                <code>{question.sampleData}</code>
              </pre>
            </div>
          )}

          {parsed.sections.map((s, i) => (
            <div className="cj-section" key={i}>
              <div className="cj-section-label">{s.label}</div>

              <div
                className={
                  s.label === "Example"
                    ? "cj-example"
                    : "cj-section-body"
                }
              >
                {s.body}
              </div>
            </div>
          ))}

          {(question.testCases || []).length > 0 && (
            <div className="cj-section">
              <div className="cj-section-label">Sample Test Cases</div>

              <div className="cj-testcases">
                {question.testCases.map((tc, i) => (
                  <div key={i} className="cj-testcase-row">
                    <span className="cj-testcase-index">
                      Case {i + 1}
                    </span>

                    {tc.label && (
                      <span className="cj-testcase-tag">
                        {tc.label}
                      </span>
                    )}

                    <code>
                      Input: {tc.input === "" ? "(none)" : tc.input}
                    </code>
                  </div>
                ))}
              </div>

              <div className="cj-note">
                Expected outputs are revealed after you submit.
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="code-judge-right">
        <div className="code-judge-toolbar">
          <span className="cj-lang-badge">
            <Code2 size={13} />
            {(question.language || "java").toUpperCase()}
          </span>

          <span className="cj-toolbar-hint">
            {isSql
              ? "Write your SQL query here"
              : "Write your solution inside the method body"}
          </span>

          {interviewId && (
            <SolutionViewer
              interviewId={interviewId}
              format="coding"
              language={question.language || (isSql ? "sql" : "java")}
              questionKey={question.questionText || question.title}
              disabled={!isSubmitted}
              disabledTooltip="Submit your solution first to view the reference solution"
              preloadedSolution={question.referenceSolution || null}
            />
          )}

          <button
            type="button"
            className="cj-reset-btn"
            onClick={onReset}
            disabled={disabled}
            title="Reset to starter code"
          >
            <RotateCcw size={13} />
            Reset
          </button>
        </div>

        <CodeEditor
          value={editorValue}
          onChange={onChange}
          disabled={disabled}
        />
      </div>
    </div>
  );
};

export const JudgeResultPanel = ({
  evaluation,
  interviewId,
  questionKey,
  language = "java",
  preloadedSolution = null,
}) => {
  if (!evaluation) return null;

  const cases = evaluation.testCaseResults || [];
  const passedCount =
    typeof evaluation.passedCount === "number"
      ? evaluation.passedCount
      : cases.filter((c) => c.passed || c.status === "PASSED").length;
  const totalCount =
    typeof evaluation.totalCount === "number"
      ? evaluation.totalCount
      : cases.length;
  const allPassed = totalCount > 0 && passedCount === totalCount;
  const score =
    typeof evaluation.score === "number"
      ? evaluation.score
      : totalCount > 0
      ? Math.round((100 * passedCount) / totalCount)
      : 0;
  const isFallback = evaluation.judgeMode === "llm-fallback";

  return (
    <div className="judge-console">
      <div className="judge-console-header">
        <FlaskConical size={15} />
        <span>
          Judge Result: <strong>{score}%</strong>
        </span>
        {totalCount > 0 && (
          <span
            style={{
              fontSize: "0.8rem",
              color: "var(--text-muted)",
              marginLeft: "0.4rem",
            }}
          >
            ({passedCount} / {totalCount} test cases passed)
          </span>
        )}

        {isFallback && (
          <span
            className="judge-fallback-badge"
            title="JDK not available; evaluated using LLM fallback"
          >
            <AlertTriangle size={12} />
            LLM Fallback (No JDK)
          </span>
        )}

        {totalCount > 0 && (
          <span
            className={`judge-verdict ${
              allPassed ? "judge-verdict-pass" : "judge-verdict-fail"
            }`}
          >
            {allPassed ? "Accepted" : `${passedCount}/${totalCount} Passed`}
          </span>
        )}
      </div>

      {evaluation.timeComplexity && (
        <div
          className="judge-complexity-banner"
          style={{
            margin: "0.75rem 1rem",
            padding: "0.75rem 1rem",
            background: "var(--bg-subtle, #f8fafc)",
            border: "1px solid var(--border-color, #e2e8f0)",
            borderRadius: "8px",
            display: "flex",
            alignItems: "flex-start",
            gap: "0.75rem",
          }}
        >
          <Clock size={18} style={{ color: "var(--primary, #6366f1)", marginTop: "2px", flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
              <span style={{ fontWeight: 700, fontSize: "0.9rem" }}>Time Complexity:</span>
              <span
                className="badge badge-tech"
                style={{
                  fontFamily: "monospace",
                  fontWeight: 700,
                  fontSize: "0.85rem",
                  padding: "0.2rem 0.5rem",
                  background: "var(--primary-subtle, #e0e7ff)",
                  color: "var(--primary, #4338ca)",
                  borderRadius: "4px",
                }}
              >
                {evaluation.timeComplexity}
              </span>
              {evaluation.spaceComplexity && (
                <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  Space Complexity: <code style={{ fontWeight: 600 }}>{evaluation.spaceComplexity}</code>
                </span>
              )}
            </div>
            {evaluation.timeComplexityExplanation && (
              <p style={{ margin: "0.35rem 0 0 0", fontSize: "0.84rem", color: "var(--text-muted)" }}>
                {evaluation.timeComplexityExplanation}
              </p>
            )}
          </div>
        </div>
      )}

      {evaluation.compileError && (
        <div className="judge-compile-error">
          <div className="judge-compile-error-head">
            <XCircle size={15} />
            <span>Compilation Error</span>
          </div>
          <pre>
            <code>{evaluation.compileError}</code>
          </pre>
        </div>
      )}

      {cases.length > 0 && (
        <div className="judge-cases">
          {cases.map((tc, i) => {
            const isPassed = tc.passed || tc.status === "PASSED";
            const statusText = tc.status || (isPassed ? "PASSED" : "FAILED");
            const expectedText = tc.expected ?? tc.expectedOutput ?? "(none)";
            const actualText =
              tc.actual !== undefined && tc.actual !== null && tc.actual !== ""
                ? tc.actual
                : tc.actualOutput !== undefined &&
                  tc.actualOutput !== null &&
                  tc.actualOutput !== ""
                ? tc.actualOutput
                : isPassed
                ? expectedText
                : "n/a";
            const errorText = tc.error || tc.failureReason;

            return (
              <div
                key={i}
                className={`judge-case ${
                  isPassed ? "judge-case-pass" : "judge-case-fail"
                }`}
              >
                <div className="judge-case-head">
                  {isPassed ? (
                    <CheckCircle2 size={15} />
                  ) : (
                    <XCircle size={15} />
                  )}

                  <strong>
                    Case {tc.id ?? i + 1}
                    {tc.label ? ` · ${tc.label}` : ""}
                  </strong>

                  <span
                    className="judge-case-status"
                    style={{
                      color: isPassed ? "var(--success)" : "var(--danger)",
                      fontWeight: 700,
                    }}
                  >
                    {statusText}
                  </span>
                </div>

                <div className="judge-case-body">
                  <div>
                    <span className="judge-case-key">Input</span>
                    <code>
                      {tc.input !== undefined &&
                      tc.input !== null &&
                      tc.input !== ""
                        ? tc.input
                        : "(none)"}
                    </code>
                  </div>

                  <div>
                    <span className="judge-case-key">Expected</span>
                    <code>{expectedText}</code>
                  </div>

                  <div>
                    <span className="judge-case-key">Actual</span>
                    <code>{actualText}</code>
                  </div>
                </div>

                {!isPassed && errorText && (
                  <div className="judge-case-reason">
                    <strong>Error:</strong> <code>{errorText}</code>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {score < 100 &&
        (evaluation.whyNot100 ||
          evaluation.scoreReason ||
          evaluation.feedback) && (
          <div className="judge-whynot100">
            <div className="judge-whynot100-head">Why not 100%</div>
            <p>
              {evaluation.whyNot100 ||
                evaluation.scoreReason ||
                evaluation.feedback}
            </p>
          </div>
        )}

      <div
        style={{
          padding: "0.85rem 1rem",
          borderTop: "1px solid var(--border-color)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "var(--bg-subtle, #f8fafc)",
          borderRadius: "0 0 10px 10px",
        }}
      >
        <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", fontWeight: 600 }}>
          Reference Solution & Explanation
        </div>
        <SolutionViewer
          interviewId={interviewId}
          format="coding"
          language={language}
          preloadedSolution={
            preloadedSolution ||
            evaluation.referenceSolution ||
            evaluation.correctedCode ||
            evaluation.correctedQuery ||
            null
          }
          questionKey={
            questionKey ||
            evaluation.questionKey ||
            evaluation.questionText ||
            evaluation.title ||
            evaluation.questionId
          }
          disabled={false}
        />
      </div>
    </div>
  );
};