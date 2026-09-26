import webbrowser
from flask import Flask, render_template_string

app = Flask(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PostgreSQL RAG App</title>
    <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
</head>
<body>
    <div id="root"></div>
    <script type="text/babel">
        function App() {
            const [info, setInfo] = React.useState({
                chat_model: 'gpt-4',
                embed_model: 'text-embedding-3-small',
                documents: [],
                chunks: []
            });
            const [messages, setMessages] = React.useState([]);

            return (
                <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
                    <h2>PostgreSQL RAG Application</h2>
                    <div>
                        <p><strong>Chat Model:</strong> {info.chat_model}</p>
                        <p><strong>Embed Model:</strong> {info.embed_model}</p>
                        <p><strong>Documents:</strong> {info.documents.length}</p>
                        <p><strong>Chunks:</strong> {info.chunks.
