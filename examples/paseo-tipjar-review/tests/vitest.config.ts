import { defineConfig } from 'vitest/config';
export default defineConfig({
  resolve: { alias: { 'react-native': 'react-native-web' } },
  test: { environment: 'jsdom', include: ['tests/**/*.test.ts', 'tests/**/*.test.tsx'] },
});
