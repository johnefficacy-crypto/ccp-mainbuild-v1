# Question Rendering Library

Headless presentational renderer for mock/study questions.

## Props
Use `QuestionRenderer({ question, mode, value, onChange, disabled, showCorrect, showExplanation })`.

## Add new type
1. Add component in `types/`.
2. Register in `QuestionRenderer.jsx` map.
3. Export from `index.js`.
4. Add story/test fixtures.
