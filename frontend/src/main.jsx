import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import DocumentsManagement from './pages/Documents.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
    {/* <DocumentsManagement/> */}
  </React.StrictMode>,
)