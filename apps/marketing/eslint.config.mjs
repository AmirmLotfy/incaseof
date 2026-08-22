import js from "@eslint/js";

export default [
  js.configs.recommended,
  { ignores: [".next/**", "node_modules/**", "next-env.d.ts"] },
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: { ecmaVersion: "latest", sourceType: "module" },
    rules: { "no-unused-vars": "off", "no-undef": "off" },
  },
];
