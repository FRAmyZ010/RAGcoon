export default function Table({ headers = [], data = [], renderRow }) {
  return (
    <div className="bg-white rounded-xl overflow-hidden shadow-sm font-mono border border-gray-100">
      <table className="w-full text-left border-collapse text-xs">
        <thead className="bg-gray-100 text-gray-600 border-b border-gray-200">
          <tr>
            {headers.map((h, i) => (
              <th key={i} className="p-4 font-semibold">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {data.map((item, index) => renderRow(item, index))}
        </tbody>
      </table>
    </div>
  );
}