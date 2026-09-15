import React, { useEffect, useMemo, useRef, useState } from 'react';

const INITIAL_DOCS = [
  { id: 'demo-1', title: 'ProjectPetFeeder', year: '2022', category: 'IOT', status: 'Processing', date: '12 Jan 2025', fileName: 'ProjectPetFeeder.pdf', size: '228 KB', demo: true },
  { id: 'demo-2', title: 'ProjectWebapplication', year: '2023', category: 'Web Application', status: 'Ready', date: '12 Jan 2025', fileName: 'ProjectWebapplication.pdf', size: '228 KB', demo: true },
  { id: 'demo-3', title: 'Networkmonitoring', year: '2023', category: 'Network', status: 'Processing', date: '12 Jan 2025', fileName: 'Networkmonitoring.pdf', size: '228 KB', demo: true },
  { id: 'demo-4', title: 'Preprojectnetwork', year: '2022', category: 'Network', status: 'Failed', date: '12 Jan 2025', fileName: 'Preprojectnetwork.pdf', size: '228 KB', demo: true },
  { id: 'demo-5', title: 'ProjectFulldocument', year: '2021', category: 'IOT', status: 'Processing', date: '12 Jan 2025', fileName: 'ProjectFulldocument.pdf', size: '228 KB', demo: true },
  { id: 'demo-6', title: 'Embeddedsystemproject', year: '2020', category: 'IOT', status: 'Processing', date: '12 Jan 2025', fileName: 'Embeddedsystemproject.pdf', size: '228 KB', demo: true },
  { id: 'demo-7', title: 'ProjectMachine', year: '2022', category: 'Machine Learning', status: 'Ready', date: '11 Jan 2025', fileName: 'ProjectMachine.pdf', size: '228 KB', demo: true },
  { id: 'demo-8', title: 'Pre-project_NU-WIFI', year: '2021', category: 'Network', status: 'Processing', date: '11 Jan 2025', fileName: 'Pre-project_NU-WIFI.pdf', size: '228 KB', demo: true },
  { id: 'demo-9', title: 'ProjectPetFeeder', year: '2022', category: 'IOT', status: 'Processing', date: '10 Jan 2025', fileName: 'ProjectPetFeeder-final.pdf', size: '228 KB', demo: true },
];

const DB_NAME = 'ragcoon-docs-db';
const STORE = 'files';

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: 'id' });
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function saveFile(file) {
  const db = await openDB();
  const record = { id: file.id, blob: file.blob };
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite');
    tx.objectStore(STORE).put(record);
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error);
  });
}

async function getFile(id) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const req = db.transaction(STORE, 'readonly').objectStore(STORE).get(id);
    req.onsuccess = () => resolve(req.result?.blob || null);
    req.onerror = () => reject(req.error);
  });
}

async function removeStoredFile(id) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite');
    tx.objectStore(STORE).delete(id);
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error);
  });
}

function readDocs() {
  try {
    return JSON.parse(localStorage.getItem('ragcoon-documents')) || INITIAL_DOCS;
  } catch {
    return INITIAL_DOCS;
  }
}

function writeDocs(docs) {
  localStorage.setItem('ragcoon-documents', JSON.stringify(docs));
}

function formatBytes(bytes) {
  if (!bytes) return '0 KB';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(i ? 1 : 0)} ${units[i]}`;
}

function formatDate(date = new Date()) {
  return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

function fileTitle(name) {
  return name.replace(/\.[^/.]+$/, '');
}

function Icon({ name, size = 16 }) {
  const common = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' };
  const paths = {
    home: <><path d="m3 10 9-7 9 7"/><path d="M5 9v11h14V9"/><path d="M9 20v-6h6v6"/></>,
    file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8M8 17h6"/></>,
    message: <><path d="M20 15a3 3 0 0 1-3 3H8l-4 3v-9a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3z"/><path d="M8 12h.01M12 12h.01M16 12h.01"/></>,
    upload: <><path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M5 20h14"/></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></>,
    more: <><circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/></>,
    download: <><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></>,
    copy: <><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M15 9V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h3"/></>,
    edit: <><path d="m4 16-.8 4.8L8 20l11-11-4-4z"/><path d="m13 6 4 4"/></>,
    trash: <><path d="M4 7h16"/><path d="M10 11v6M14 11v6"/><path d="m6 7 1 14h10l1-14M9 7V4h6v3"/></>,
    logout: <><path d="M10 17l5-5-5-5"/><path d="M15 12H3"/><path d="M21 4v16"/></>,
    chevron: <path d="m6 9 6 6 6-6"/>,
    check: <path d="m5 12 4 4L19 6"/>,
  };
  return <svg {...common}>{paths[name]}</svg>;
}

export default function App() {
  const [docs, setDocs] = useState(readDocs);
  const [menuId, setMenuId] = useState(null);
  const [filterCategory, setFilterCategory] = useState('Category');
  const [filterModified, setFilterModified] = useState('Modified');
  const [filterYear, setFilterYear] = useState('Years');
  const [activeNav, setActiveNav] = useState('Documents Management');
  const [toast, setToast] = useState('');
  const [recent, setRecent] = useState(() => readDocs().filter(d => !d.demo).slice(0, 3));
  const inputRef = useRef(null);

  useEffect(() => writeDocs(docs), [docs]);

  useEffect(() => {
    const close = () => setMenuId(null);
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(''), 2500);
    return () => clearTimeout(t);
  }, [toast]);

  const categories = useMemo(() => ['Category', ...new Set(docs.map(d => d.category))], [docs]);
  const years = useMemo(() => ['Years', ...new Set(docs.map(d => d.year))], [docs]);

  const filteredDocs = useMemo(() => docs.filter(d =>
    (filterCategory === 'Category' || d.category === filterCategory) &&
    (filterYear === 'Years' || d.year === filterYear)
  ), [docs, filterCategory, filterYear]);

  function notify(message) {
    setToast(message);
  }

  async function handleUpload(event) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;

    const newDocs = [];
    for (const file of files) {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const ext = file.name.split('.').pop()?.toLowerCase();
      const category = ext === 'pdf' ? 'PDF' : ['doc', 'docx'].includes(ext) ? 'Document' : 'Other';
      const doc = {
        id,
        title: fileTitle(file.name),
        year: String(new Date().getFullYear()),
        category,
        status: 'Processing',
        date: formatDate(),
        fileName: file.name,
        size: formatBytes(file.size),
        demo: false
      };
      await saveFile({ id, blob: file });
      newDocs.push(doc);
    }

    setDocs(prev => [...newDocs, ...prev]);
    setRecent(prev => [...newDocs, ...prev].slice(0, 3));
    notify(`${files.length} file${files.length > 1 ? 's' : ''} uploaded successfully`);
    event.target.value = '';
  }

  async function handleDownload(doc) {
    const blob = await getFile(doc.id);
    if (!blob) {
      notify('This sample file has no local file data');
      return;
    }
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = doc.fileName || doc.title;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    notify('Download started');
  }

  async function handleCopy(doc) {
    try {
      await navigator.clipboard.writeText(doc.fileName || doc.title);
      notify('File name copied');
    } catch {
      notify('Copy is not available in this browser');
    }
  }

  function handleRename(doc) {
    const next = window.prompt('Rename document', doc.title);
    if (!next?.trim()) return;
    setDocs(prev => prev.map(d => d.id === doc.id ? { ...d, title: next.trim() } : d));
    setRecent(prev => prev.map(d => d.id === doc.id ? { ...d, title: next.trim() } : d));
    setMenuId(null);
    notify('Document renamed');
  }

  async function handleRemove(doc) {
    const ok = window.confirm(`Remove "${doc.title}"?`);
    if (!ok) return;
    setDocs(prev => prev.filter(d => d.id !== doc.id));
    setRecent(prev => prev.filter(d => d.id !== doc.id));
    if (!doc.demo) await removeStoredFile(doc.id);
    setMenuId(null);
    notify('Document removed');
  }

  function resetDemo() {
    setDocs(INITIAL_DOCS);
    setRecent([]);
    notify('Demo documents restored');
  }

  return (
    <div className="app-shell" onClick={() => setMenuId(null)}>
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-logo">🦝</div>
          <div className="brand-name">RAGcoon</div>
          <div className="collapse-icon">▯</div>
        </div>

        <nav className="nav">
          {[
            ['Dashboard', 'home'],
            ['Documents Management', 'file'],
            ['Feedback', 'message']
          ].map(([label, icon]) => (
            <button
              key={label}
              className={`nav-item ${activeNav === label ? 'active' : ''}`}
              onClick={(e) => { e.stopPropagation(); setActiveNav(label); notify(`${label} selected`); }}
            >
              <Icon name={icon} size={13} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <button className="logout" onClick={() => notify('Logged out (demo)')}>
          <span>Log Out</span>
          <Icon name="logout" size={13} />
        </button>
      </aside>

      <main className="main">
        <header className="topbar">
          <div />
          <div className="account">
            <button className="icon-button" onClick={() => notify('No new notifications')}>
              <Icon name="bell" size={15} />
            </button>
            <span className="avatar-dot" />
            <span className="username">Harry Jann</span>
          </div>
        </header>

        {activeNav !== 'Documents Management' ? (
          <section className="empty-section">
            <h2>{activeNav}</h2>
            <p>This navigation item is ready for your next page.</p>
            <button className="primary" onClick={() => setActiveNav('Documents Management')}>Back to Documents</button>
          </section>
        ) : (
          <section className="content">
            <div className="page-heading">
              <h1>Documents Management</h1>
              <button className="upload-button" onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}>
                <Icon name="upload" size={14} />
                Upload file
              </button>
              <input ref={inputRef} type="file" multiple hidden accept=".pdf,.doc,.docx,.txt,.csv,.ppt,.pptx,.xlsx,.zip" onChange={handleUpload} />
            </div>

            <div className="recent-header">
              <h2>Recently modified</h2>
              <div className="sparkles" aria-hidden="true"><span>✦</span><span>✦</span></div>
            </div>

            <div className="recent-grid">
              {(recent.length ? recent : docs.slice(0, 3)).map(doc => (
                <div className="recent-card" key={doc.id}>
                  <Icon name="file" size={13} />
                  <div className="recent-text">
                    <div className="recent-title">{doc.title}</div>
                    <div className="recent-meta">{doc.size} &nbsp; {doc.fileName?.split('.').pop()?.toUpperCase() || 'PDF'}</div>
                  </div>
                  <button className="card-more" onClick={(e) => { e.stopPropagation(); setMenuId(menuId === doc.id ? null : doc.id); }}>
                    <Icon name="more" size={14} />
                  </button>
                </div>
              ))}
            </div>

            <div className="files-header">
              <h2>All files</h2>
              <div className="filters" onClick={(e) => e.stopPropagation()}>
                <select value={filterCategory} onChange={e => setFilterCategory(e.target.value)}>
                  {categories.map(c => <option key={c}>{c}</option>)}
                </select>
                <select value={filterModified} onChange={e => setFilterModified(e.target.value)}>
                  <option>Modified</option>
                  <option>Newest</option>
                  <option>Oldest</option>
                </select>
                <select value={filterYear} onChange={e => setFilterYear(e.target.value)}>
                  {years.map(y => <option key={y}>{y}</option>)}
                </select>
              </div>
            </div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Year</th>
                    <th>Category</th>
                    <th>Status</th>
                    <th>Date</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {filteredDocs.length ? filteredDocs.map(doc => (
                    <tr key={doc.id}>
                      <td><div className="title-cell"><span className="pdf-mark">▧</span>{doc.title}</div></td>
                      <td>{doc.year}</td>
                      <td>{doc.category}</td>
                      <td><span className={`status ${doc.status.toLowerCase()}`}>{doc.status}</span></td>
                      <td>{doc.date}</td>
                      <td className="menu-cell">
                        <button className="row-more" onClick={(e) => { e.stopPropagation(); setMenuId(menuId === doc.id ? null : doc.id); }}>
                          <Icon name="more" size={15} />
                        </button>
                        {menuId === doc.id && (
                          <div className="context-menu" onClick={e => e.stopPropagation()}>
                            <button onClick={() => handleDownload(doc)}><Icon name="download" size={14} />Download</button>
                            <button onClick={() => handleCopy(doc)}><Icon name="copy" size={14} />Copy</button>
                            <button onClick={() => handleRename(doc)}><Icon name="edit" size={14} />Rename</button>
                            <button className="danger" onClick={() => handleRemove(doc)}><Icon name="trash" size={14} />Remove</button>
                          </div>
                        )}
                      </td>
                    </tr>
                  )) : (
                    <tr><td colSpan="6" className="no-files">No documents found.</td></tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="bottom-actions">
              <span>{filteredDocs.length} document{filteredDocs.length !== 1 ? 's' : ''}</span>
              <button onClick={resetDemo}>Restore demo data</button>
            </div>
          </section>
        )}

        {toast && <div className="toast"><Icon name="check" size={15} />{toast}</div>}
      </main>
    </div>
  );
}
