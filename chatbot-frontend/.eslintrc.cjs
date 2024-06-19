module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'airbnb',
    'airbnb-typescript',
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended-type-checked',
    'plugin:react-hooks/recommended',
    'plugin:@typescript-eslint/stylistic-type-checked',
    'plugin:react/recommended',
    'plugin:react/jsx-runtime'
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs'],
  parser: '@typescript-eslint/parser',
  plugins: ['react-refresh'],
  rules: {
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true },
    ],
    'react/jsx-filename-extension': ["error", { extensions: [".tsx"] }],
    'import/no-extraneous-dependencies': ["error", {
      devDependencies: ['vite.config.ts']
    }],
    "react/jsx-props-no-spreading": ["error", { "custom": "ignore" }],
    "react/require-default-props": "off",
    "react/jsx-no-bind": "off",
    "@typescript-eslint/no-misused-promises": ["error", { checksVoidReturn: false }]
  },
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    project: ['./tsconfig.json', './tsconfig.node.json'],
    tsconfigRootDir: __dirname,
  },
  settings: {
    react: {
      version: "detect"
    }
  }
}
