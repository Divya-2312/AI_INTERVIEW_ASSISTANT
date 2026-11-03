// ai-service/app/services/code_executor.py:44-93
public class MockMateRunner {
    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: MockMateRunner <TargetClassName> [InputString]");
            System.exit(1);
        }
        String targetClassName = args[0];
        String rawInput = args.length > 1 ? args[1] : "";

        try {
            Class<?> targetClass = Class.forName(targetClassName);
            Method[] methods = targetClass.getDeclaredMethods();
            Method targetMethod = null;

            for (Method m : methods) {
                if (!m.getName().equals("main") && !Modifier.isPrivate(m.getModifiers()) && !m.isSynthetic()) {
                    targetMethod = m;
                    break;
                }
            }
            if (targetMethod == null) {
                System.err.println("No executable method found in class " + targetClassName);
                System.exit(2);
            }

            targetMethod.setAccessible(true);
            Object targetInstance = Modifier.isStatic(targetMethod.getModifiers()) ? null : targetClass.getDeclaredConstructor().newInstance();
            Class<?>[] paramTypes = targetMethod.getParameterTypes();
            Object[] invokedArgs = parseArguments(rawInput, paramTypes);

            Object result = targetMethod.invoke(targetInstance, invokedArgs);
            System.out.print(formatOutput(result));
        } catch (InvocationTargetException ite) {
            Throwable cause = ite.getCause() != null ? ite.getCause() : ite;
            System.err.println("RUNTIME_ERROR: " + cause.toString());
            System.exit(3);
        }
    }
}
