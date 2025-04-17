const globals = require("globals");
const js = require("@eslint/js");
const prettier = require("eslint-config-prettier");

module.exports = [
  {
    ignores: ["src/**/*.test.js", "**/*.js"],
  },
  js.configs.recommended,
  prettier,
  {
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.jquery,
        ...globals.node,
        frappe: "readonly",
        erpnext: "readonly",
        __: "readonly",
        locals: "readonly",
        cint: "readonly",
        in_list: "readonly",
        moment: "readonly",
      },
      ecmaVersion: 2022,
      sourceType: "script",
    },
  },
];
