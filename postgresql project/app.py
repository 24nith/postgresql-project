```

Let's write out the React component structure in detail inside a `<script type="text/babel">`:

Components & State:
1. `App`:
   - `info`: `{ chat_model, embed_model, documents: [], chunks: [] }`
   - `messages`: `[{ role: 'user' | 'assistant', content: '...', sources: [...] }]
