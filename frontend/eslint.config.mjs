import nextVitals from 'eslint-config-next/core-web-vitals'
import nextTypescript from 'eslint-config-next/typescript'

const eslintConfig = [
  ...nextVitals,
  ...nextTypescript,
  {
    rules: {
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-empty-object-type': 'warn',
      'react/no-unescaped-entities': 'warn',
      // React Compiler is not enabled. Its compiler-only diagnostics flag the
      // normal data-fetching effects used by this application, so keep them off.
      'react-hooks/immutability': 'warn',
      'react-hooks/preserve-manual-memoization': 'off',
      'react-hooks/purity': 'warn',
      'react-hooks/set-state-in-effect': 'off',
    },
  },
]

export default eslintConfig
