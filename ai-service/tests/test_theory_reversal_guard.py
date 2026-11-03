import unittest

from app.models.llama_provider import (
    _check_swapped_properties,
    _split_reference_key_points,
)


class TestTheoryReversalGuard(unittest.TestCase):
    def test_entity_and_entity_set_reversal_is_detected(self):
        question = "What is an entity and an entity set in the ER model?"
        reference = (
            "An entity is a real-world object or concept with attributes. "
            "An entity set is a collection of similar entities, typically mapped to a table."
        )
        reversed_answer = (
            "An entity set is a single real-world object, while an entity is a collection "
            "of similar tables."
        )
        correct_answer = (
            "An entity is a single real-world object, while an entity set is a collection "
            "of similar entities."
        )

        self.assertTrue(any(
            _check_swapped_properties(question, reversed_answer, reference, point)
            for point in _split_reference_key_points(reference)
        ))
        self.assertFalse(any(
            _check_swapped_properties(question, correct_answer, reference, point)
            for point in _split_reference_key_points(reference)
        ))

    def test_dirty_and_non_repeatable_read_reversal_is_detected(self):
        question = "What is the difference between a dirty read and a non-repeatable read?"
        reference = (
            "A dirty read occurs when a transaction reads uncommitted modifications that might "
            "later roll back. A non-repeatable read occurs when a transaction rereads a row "
            "after another transaction commits a change."
        )
        reversed_answer = (
            "A dirty read occurs when reading committed data, while a non-repeatable read "
            "happens when reading uncommitted changes that roll back."
        )
        correct_answer = (
            "A dirty read means a query views changes that another transaction made but hasn't "
            "committed yet, which might get rolled back. A non-repeatable read occurs when you "
            "read a row, and then another transaction commits an update to that row."
        )

        self.assertTrue(any(
            _check_swapped_properties(question, reversed_answer, reference, point)
            for point in _split_reference_key_points(reference)
        ))
        self.assertFalse(any(
            _check_swapped_properties(question, correct_answer, reference, point)
            for point in _split_reference_key_points(reference)
        ))


if __name__ == "__main__":
    unittest.main()
