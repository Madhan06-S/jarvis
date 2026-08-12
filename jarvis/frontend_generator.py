from jinja2 import Template
from pathlib import Path
from typing import Dict
from spec_engine import AppSpec

class FrontendGenerator:
    def __init__(self):
        self.templates = self._load_templates()
    
    def _load_templates(self):
        return {
            "api_client": Template("""
// Auto-generated API client for {{app_name}}
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(public status: number, public data: any) {
    super(`API Error ${status}`);
  }
}

async function fetchApi(endpoint: string, options: RequestInit = {}) {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` }),
    ...((options.headers as Record<string, string>) || {})
  };
  
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(response.status, error);
  }
  
  return response.json();
}

{% if auth %}
export const authApi = {
  login: (email: string, password: string) => 
    fetchApi('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username: email, password })
    }),
  
  register: (data: { email: string; password: string; full_name: string }) =>
    fetchApi('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  
  me: () => fetchApi('/auth/me'),
  
  logout: () => { localStorage.removeItem('token'); }
};
{% endif %}

{% for model in models %}
export interface {{model.name}} {
  id: number;
  {% for field in model.fields if field.type != "relation" %}
  {{field.name}}: {% if field.type == "string" or field.type == "text" or field.type == "date" or field.type == "email" or field.type == "file" %}string{% elif field.type == "number" %}number{% elif field.type == "boolean" %}boolean{% elif field.type == "json" %}Record<string, any>{% else %}string{% endif %};
  {% endfor %}
  created_at: string;
  updated_at: string;
}

export interface {{model.name}}ListResponse {
  data: {{model.name}}[];
  total: number;
  page: number;
  page_size: number;
}

export const {{model.name.lower()}}Api = {
  list: (params?: { page?: number; page_size?: number; search?: string; sort_by?: string; sort_order?: string }) =>
    fetchApi(`/{{model.name.lower()}}s?${new URLSearchParams(params as any)}`),
  
  get: (id: number) => fetchApi(`/{{model.name.lower()}}s/${id}`),
  
  create: (data: Partial<{{model.name}}>) => 
    fetchApi(`/{{model.name.lower()}}s`, { method: 'POST', body: JSON.stringify(data) }),
  
  update: (id: number, data: Partial<{{model.name}}>) =>
    fetchApi(`/{{model.name.lower()}}s/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  
  delete: (id: number) =>
    fetchApi(`/{{model.name.lower()}}s/${id}`, { method: 'DELETE' }),
};
{% endfor %}
"""),
            
            "list_page": Template("""
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { {{model.name.lower()}}Api, {{model.name}} } from '../api/client';
import { DataTable } from '../components/DataTable';
import { SearchBar } from '../components/SearchBar';
import { Pagination } from '../components/Pagination';
import { Button } from '../components/Button';
import { Plus, Pencil, Trash2 } from 'lucide-react';

export function {{model.name}}ListPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<{{model.name}}[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const fetchItems = async () => {
    try {
      setLoading(true);
      const response = await {{model.name.lower()}}Api.list({
        page,
        page_size: pageSize,
        search: search || undefined,
        sort_by: sortBy,
        sort_order: sortOrder
      });
      setItems(response.data);
      setTotal(response.total);
    } catch (err: any) {
      setError(err.data?.detail || 'Failed to load items');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, [page, search, sortBy, sortOrder]);

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure?')) return;
    try {
      await {{model.name.lower()}}Api.delete(id);
      fetchItems();
    } catch (err: any) {
      setError(err.data?.detail || 'Delete failed');
    }
  };

  const columns = [
    {% for field in model.fields if field.type != "relation" %}
    { 
      key: '{{field.name}}', 
      label: '{{field.name.replace("_", " ").title()}}',
      sortable: true,
      {% if field.type == "boolean" %}
      render: (value: boolean) => (
        <span className={`px-2 py-1 rounded-full text-xs ${value ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
          {value ? 'Yes' : 'No'}
        </span>
      )
      {% elif field.type == "date" %}
      render: (value: string) => value ? new Date(value).toLocaleDateString() : '-'
      {% endif %}
    },
    {% endfor %}
    {
      key: 'actions',
      label: 'Actions',
      render: (_: any, item: {{model.name}}) => (
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => navigate(`/{{model.name.lower()}}s/${item.id}/edit`)}>
            <Pencil className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => handleDelete(item.id)}>
            <Trash2 className="w-4 h-4 text-red-500" />
          </Button>
        </div>
      )
    }
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">{{model.name}}s</h1>
        <Button onClick={() => navigate('/{{model.name.lower()}}s/new')}>
          <Plus className="w-4 h-4 mr-2" /> New {{model.name}}
        </Button>
      </div>
      
      <SearchBar value={search} onChange={setSearch} placeholder="Search {{model.name.lower()}}s..." />
      
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}
      
      <DataTable
        columns={columns}
        data={items}
        loading={loading}
        sortBy={sortBy}
        sortOrder={sortOrder}
        onSort={(key) => {
          if (sortBy === key) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
          } else {
            setSortBy(key);
            setSortOrder('asc');
          }
        }}
      />
      
      <Pagination
        page={page}
        pageSize={pageSize}
        total={total}
        onPageChange={setPage}
      />
    </div>
  );
}
"""),
            
            "form_page": Template("""
import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { {{model.name.lower()}}Api, {{model.name}} } from '../api/client';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { TextArea } from '../components/TextArea';
import { Select } from '../components/Select';
import { Checkbox } from '../components/Checkbox';

export function {{model.name}}FormPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = Boolean(id);
  
  const [formData, setFormData] = useState<Partial<{{model.name}}>>({});
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isEdit) {
      {{model.name.lower()}}Api.get(Number(id)).then(response => {
        setFormData(response.data);
        setLoading(false);
      }).catch(err => {
        setError(err.data?.detail || 'Failed to load');
        setLoading(false);
      });
    }
  }, [id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (isEdit) {
        await {{model.name.lower()}}Api.update(Number(id), formData);
      } else {
        await {{model.name.lower()}}Api.create(formData);
      }
      navigate('/{{model.name.lower()}}s');
    } catch (err: any) {
      setError(err.data?.detail || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="p-6">Loading...</div>;

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">
        {isEdit ? 'Edit' : 'New'} {{model.name}}
      </h1>
      
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="space-y-4">
        {% for field in model.fields if field.type != "relation" %}
        <div>
          <label className="block text-sm font-medium mb-1">
            {{field.name.replace("_", " ").title()}}
            {% if field.required %}<span className="text-red-500">*</span>{% endif %}
          </label>
          {% if field.type == "text" %}
          <TextArea
            value={formData.{{field.name}} || ''}
            onChange={(e) => setFormData({ ...formData, {{field.name}}: e.target.value })}
            required={% if field.required %}true{% else %}false{% endif %}
          />
          {% elif field.type == "boolean" %}
          <Checkbox
            checked={formData.{{field.name}} || false}
            onChange={(e) => setFormData({ ...formData, {{field.name}}: e.target.checked })}
          />
          {% elif field.type == "number" %}
          <Input
            type="number"
            value={formData.{{field.name}} || ''}
            onChange={(e) => setFormData({ ...formData, {{field.name}}: Number(e.target.value) })}
            required={% if field.required %}true{% else %}false{% endif %}
          />
          {% elif field.type == "date" %}
          <Input
            type="datetime-local"
            value={formData.{{field.name}} ? new Date(formData.{{field.name}}).toISOString().slice(0, 16) : ''}
            onChange={(e) => setFormData({ ...formData, {{field.name}}: new Date(e.target.value).toISOString() })}
            required={% if field.required %}true{% else %}false{% endif %}
          />
          {% elif field.type == "email" %}
          <Input
            type="email"
            value={formData.{{field.name}} || ''}
            onChange={(e) => setFormData({ ...formData, {{field.name}}: e.target.value })}
            required={% if field.required %}true{% else %}false{% endif %}
          />
          {% elif field.options %}
          <Select
            value={formData.{{field.name}} || ''}
            onChange={(e) => setFormData({ ...formData, {{field.name}}: e.target.value })}
            options={[
              {% for opt in field.options %}
              { value: '{{opt}}', label: '{{opt}}' },
              {% endfor %}
            ]}
            required={% if field.required %}true{% else %}false{% endif %}
          />
          {% else %}
          <Input
            value={formData.{{field.name}} || ''}
            onChange={(e) => setFormData({ ...formData, {{field.name}}: e.target.value })}
            required={% if field.required %}true{% else %}false{% endif %}
          />
          {% endif %}
        </div>
        {% endfor %}
        
        <div className="flex gap-4 pt-4">
          <Button type="submit" disabled={saving}>
            {saving ? 'Saving...' : isEdit ? 'Update' : 'Create'}
          </Button>
          <Button type="button" variant="outline" onClick={() => navigate('/{{model.name.lower()}}s')}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
"""),
            
            "main_app": Template("""
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
{% if auth %}
import { AuthProvider } from './contexts/AuthContext';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { ProtectedRoute } from './components/ProtectedRoute';
{% endif %}
{% for model in models %}
import { {{model.name}}ListPage } from './pages/{{model.name}}ListPage';
import { {{model.name}}FormPage } from './pages/{{model.name}}FormPage';
{% endfor %}
import { DashboardPage } from './pages/DashboardPage';
import { Layout } from './components/Layout';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      {% if auth %}<AuthProvider>{% endif %}
      <BrowserRouter>
        <Routes>
          {% if auth %}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          {% endif %}
          <Route element={<Layout />}>
            <Route path="/" element={<DashboardPage />} />
            {% for model in models %}
            <Route path="/{{model.name.lower()}}s" element={
              {% if auth %}<ProtectedRoute>{% endif %}<{{model.name}}ListPage />{% if auth %}</ProtectedRoute>{% endif %}
            } />
            <Route path="/{{model.name.lower()}}s/new" element={
              {% if auth %}<ProtectedRoute>{% endif %}<{{model.name}}FormPage />{% if auth %}</ProtectedRoute>{% endif %}
            } />
            <Route path="/{{model.name.lower()}}s/:id/edit" element={
              {% if auth %}<ProtectedRoute>{% endif %}<{{model.name}}FormPage />{% if auth %}</ProtectedRoute>{% endif %}
            } />
            {% endfor %}
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" />
      {% if auth %}</AuthProvider>{% endif %}
    </QueryClientProvider>
  );
}

export default App;
"""),
            
            "package_json": Template("""
{
  "name": "{{app_name.lower().replace(' ', '-')}}-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.0",
    "@tanstack/react-query": "^5.17.0",
    "lucide-react": "^0.303.0",
    "sonner": "^1.3.1",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.2.0",
    "recharts": "^2.10.3"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.2.2",
    "vite": "^5.0.8"
  }
}
"""),
            
            "vite_config": """
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\\/api/, '')
      }
    }
  }
})
""",
            
            "tailwind_config": """
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
""",
            
            "index_css": """
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply bg-gray-50 text-gray-900 dark:bg-gray-900 dark:text-gray-100;
  }
}
""",
            
            "html": Template("""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{{app_name}}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""),
            
            "main_tsx": """
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
""",
            
            "env_example": """
VITE_API_URL=http://localhost:8000
"""
        }
    
    def generate(self, spec: AppSpec) -> Dict[str, str]:
        files = {}
        
        # API Client
        files["frontend/src/api/client.ts"] = self.templates["api_client"].render(
            app_name=spec.name,
            models=spec.models,
            auth=spec.auth
        )
        
        # Pages for each model
        for model in spec.models:
            files[f"frontend/src/pages/{model.name}ListPage.tsx"] = self.templates["list_page"].render(
                model=model
            )
            files[f"frontend/src/pages/{model.name}FormPage.tsx"] = self.templates["form_page"].render(
                model=model
            )
        
        # Main App
        files["frontend/src/App.tsx"] = self.templates["main_app"].render(
            models=spec.models,
            auth=spec.auth
        )
        
        # Config files
        files["frontend/package.json"] = self.templates["package_json"].render(app_name=spec.name)
        files["frontend/vite.config.ts"] = self.templates["vite_config"]
        files["frontend/tailwind.config.js"] = self.templates["tailwind_config"]
        files["frontend/src/index.css"] = self.templates["index_css"]
        files["frontend/index.html"] = self.templates["html"].render(app_name=spec.name)
        files["frontend/src/main.tsx"] = self.templates["main_tsx"]
        files["frontend/.env.example"] = self.templates["env_example"]
        
        # Shared components
        files["frontend/src/lib/utils.ts"] = self._lib_utils()
        files["frontend/src/components/DataTable.tsx"] = self._data_table_component()
        files["frontend/src/components/SearchBar.tsx"] = self._search_bar_component()
        files["frontend/src/components/Pagination.tsx"] = self._pagination_component()
        files["frontend/src/components/Button.tsx"] = self._button_component()
        files["frontend/src/components/Input.tsx"] = self._input_component()
        files["frontend/src/components/TextArea.tsx"] = self._text_area_component()
        files["frontend/src/components/Select.tsx"] = self._select_component()
        files["frontend/src/components/Checkbox.tsx"] = self._checkbox_component()
        files["frontend/src/components/Layout.tsx"] = self._layout_component(spec)
        files["frontend/src/pages/DashboardPage.tsx"] = self._dashboard_page(spec)
        files["frontend/src/hooks/useRealtime.ts"] = self._use_realtime_hook()
        files["frontend/src/components/charts/RevenueChart.tsx"] = self._revenue_chart_component()
        
        if spec.auth:
            files["frontend/src/contexts/AuthContext.tsx"] = self._auth_context()
            files["frontend/src/components/ProtectedRoute.tsx"] = self._protected_route()
            files["frontend/src/pages/LoginPage.tsx"] = self._login_page()
            files["frontend/src/pages/RegisterPage.tsx"] = self._register_page()
        
        return files
    
    def _lib_utils(self):
        return """import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
"""

    def _data_table_component(self):
        return """
import { ChevronUp, ChevronDown } from 'lucide-react';

interface Column {
  key: string;
  label: string;
  sortable?: boolean;
  render?: (value: any, row: any) => React.ReactNode;
}

interface DataTableProps {
  columns: Column[];
  data: any[];
  loading?: boolean;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  onSort?: (key: string) => void;
}

export function DataTable({ columns, data, loading, sortBy, sortOrder, onSort }: DataTableProps) {
  if (loading) return <div className="animate-pulse bg-gray-200 h-64 rounded-lg" />;
  
  return (
    <div className="overflow-x-auto border rounded-lg">
      <table className="w-full text-sm text-left">
        <thead className="bg-gray-50 dark:bg-gray-800 text-xs uppercase">
          <tr>
            {columns.map(col => (
              <th 
                key={col.key} 
                className="px-6 py-3 font-medium cursor-pointer select-none"
                onClick={() => col.sortable && onSort?.(col.key)}
              >
                <div className="flex items-center gap-1">
                  {col.label}
                  {col.sortable && sortBy === col.key && (
                    sortOrder === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr><td colSpan={columns.length} className="px-6 py-8 text-center text-gray-500">No items found</td></tr>
          ) : (
            data.map((row, i) => (
              <tr key={row.id || i} className="border-t hover:bg-gray-50 dark:hover:bg-gray-800">
                {columns.map(col => (
                  <td key={col.key} className="px-6 py-4">
                    {col.render ? col.render(row[col.key], row) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
"""
    
    def _search_bar_component(self):
        return """
import { Search } from 'lucide-react';

export function SearchBar({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder || 'Search...'}
        className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
      />
    </div>
  );
}
"""
    
    def _pagination_component(self):
        return """
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from './Button';

export function Pagination({ page, pageSize, total, onPageChange }: any) {
  const totalPages = Math.ceil(total / pageSize) || 1;
  
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-gray-600">
        Showing {total === 0 ? 0 : ((page - 1) * pageSize) + 1} to {Math.min(page * pageSize, total)} of {total}
      </span>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" onClick={() => onPageChange(page - 1)} disabled={page <= 1}>
          <ChevronLeft className="w-4 h-4" />
        </Button>
        <span className="px-3 py-1 text-sm">Page {page} of {totalPages}</span>
        <Button variant="outline" size="sm" onClick={() => onPageChange(page + 1)} disabled={page >= totalPages}>
          <ChevronRight className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}
"""
    
    def _button_component(self):
        return """
import { cn } from '../lib/utils';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'default' | 'sm' | 'lg';
}

export function Button({ className, variant = 'default', size = 'default', ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center rounded-md font-medium transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
        'disabled:pointer-events-none disabled:opacity-50',
        variant === 'default' && 'bg-blue-600 text-white hover:bg-blue-700',
        variant === 'outline' && 'border border-gray-300 bg-transparent hover:bg-gray-100',
        variant === 'ghost' && 'hover:bg-gray-100',
        size === 'default' && 'h-9 px-4 py-2',
        size === 'sm' && 'h-8 px-3 text-xs',
        size === 'lg' && 'h-10 px-8',
        className
      )}
      {...props}
    />
  );
}
"""
    
    def _input_component(self):
        return """
import { cn } from '../lib/utils';

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        'flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm',
        'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className
      )}
      {...props}
    />
  );
}
"""

    def _text_area_component(self):
        return """
import { cn } from '../lib/utils';

export function TextArea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        'flex min-h-[80px] w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm',
        'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className
      )}
      {...props}
    />
  );
}
"""

    def _select_component(self):
        return """
import { cn } from '../lib/utils';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  options: { value: string; label: string }[];
}

export function Select({ className, options, ...props }: SelectProps) {
  return (
    <select
      className={cn(
        'flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm',
        'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className
      )}
      {...props}
    >
      <option value="">Select option</option>
      {options.map(opt => (
        <option key={opt.value} value={opt.value}>{opt.label}</option>
      ))}
    </select>
  );
}
"""

    def _checkbox_component(self):
        return """
export function Checkbox({ checked, onChange, label }: { checked?: boolean; onChange: (e: React.ChangeEvent<HTMLInputElement>) => void; label?: string }) {
  return (
    <label className="flex items-center space-x-2 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
      />
      {label && <span className="text-sm font-medium">{label}</span>}
    </label>
  );
}
"""

    def _layout_component(self, spec: AppSpec):
        items = []
        for m in spec.models:
            items.append(
                f'          <NavLink to="/{m.name.lower()}s" className={{({{ isActive }}) => `block px-4 py-2 rounded-lg ${{isActive ? "bg-blue-50 text-blue-700 font-semibold" : "text-gray-600 hover:bg-gray-50"}}`}}>\n'
                f'            {m.name}s\n'
                f'          </NavLink>'
            )
        nav_items = "\n".join(items)
        
        auth_import = 'import { useAuth } from "../contexts/AuthContext";' if spec.auth else ''
        auth_hook = 'const { user, logout } = useAuth();' if spec.auth else ''
        auth_footer = (
          '<div className="p-4 border-t"><div className="flex items-center gap-3 mb-2"><User className="w-8 h-8 text-gray-400" />'
          '<div className="flex-1 min-w-0"><p className="text-sm font-medium truncate">{user?.full_name}</p>'
          '<p className="text-xs text-gray-500 truncate">{user?.email}</p></div></div>'
          '<button onClick={logout} className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm text-red-600 bg-red-50 hover:bg-red-100 rounded-md">'
          '<LogOut className="w-4 h-4" /> Sign Out</button></div>'
        ) if spec.auth else ''

        return f"""import {{ NavLink, Outlet }} from 'react-router-dom';
import {{ LayoutDashboard, LogOut, User }} from 'lucide-react';
{auth_import}

export function Layout() {{
  {auth_hook}
  
  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      <aside className="w-64 bg-white dark:bg-gray-800 border-r flex flex-col justify-between">
        <div>
          <div className="p-6">
            <h1 className="text-xl font-bold text-blue-600">{spec.name}</h1>
          </div>
          <nav className="px-4 space-y-1">
            <NavLink to="/" className={{({{ isActive }}) => `block px-4 py-2 rounded-lg ${{isActive ? "bg-blue-50 text-blue-700 font-semibold" : "text-gray-600 hover:bg-gray-50"}}`}}>
              <LayoutDashboard className="w-4 h-4 inline mr-2" /> Dashboard
            </NavLink>
            {nav_items}
          </nav>
        </div>
        {auth_footer}
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}}
"""
    
    def _dashboard_page(self, spec: AppSpec):
        cards = "".join([f"""
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border">
            <h3 className="text-lg font-semibold mb-2">{m.name}s</h3>
            <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">Manage and explore your {m.name.lower()} records</p>
            <NavLink to="/{m.name.lower()}s" className="text-blue-600 font-medium hover:underline text-sm">Manage {m.name}s →</NavLink>
          </div>
        """ for m in spec.models])
        
        return f"""
import {{ NavLink }} from 'react-router-dom';

export function DashboardPage() {{
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">{spec.name} Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {cards if cards else '<p className="text-gray-500">No modules configured yet.</p>'}
      </div>
    </div>
  );
}}
"""
    
    def _auth_context(self):
        return """
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authApi } from '../api/client';

interface User {
  id: number;
  email: string;
  full_name: string;
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; password: string; full_name: string }) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      authApi.me().then(response => {
        setUser(response);
      }).catch(() => {
        localStorage.removeItem('token');
      }).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    const response = await authApi.login(email, password);
    localStorage.setItem('token', response.access_token);
    const userData = await authApi.me();
    setUser(userData);
  };

  const register = async (data: { email: string; password: string; full_name: string }) => {
    await authApi.register(data);
    await login(data.email, data.password);
  };

  const logout = () => {
    authApi.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
"""
    
    def _protected_route(self):
        return """
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  
  if (loading) return <div className="flex items-center justify-center h-screen">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  
  return <>{children}</>;
}
"""
    
    def _login_page(self):
        return """
import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/Button';
import { Input } from '../components/Input';

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      navigate('/');
    } catch (err: any) {
      setError(err.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-lg">
        <h1 className="text-2xl font-bold text-center mb-6">Sign In</h1>
        {error && <div className="bg-red-50 text-red-700 p-3 rounded mb-4 text-sm">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <Input type="email" value={email} onChange={e => setEmail(e.target.value)} required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <Input type="password" value={password} onChange={e => setPassword(e.target.value)} required />
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </Button>
        </form>
        <p className="text-center text-sm text-gray-600 mt-4">
          Don't have an account? <Link to="/register" className="text-blue-600 hover:underline">Register</Link>
        </p>
      </div>
    </div>
  );
}
"""

    def _register_page(self):
        return """
import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/Button';
import { Input } from '../components/Input';

export function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await register({ full_name: fullName, email, password });
      navigate('/');
    } catch (err: any) {
      setError(err.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-lg">
        <h1 className="text-2xl font-bold text-center mb-6">Create Account</h1>
        {error && <div className="bg-red-50 text-red-700 p-3 rounded mb-4 text-sm">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Full Name</label>
            <Input value={fullName} onChange={e => setFullName(e.target.value)} required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <Input type="email" value={email} onChange={e => setEmail(e.target.value)} required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <Input type="password" value={password} onChange={e => setPassword(e.target.value)} required />
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Creating account...' : 'Register'}
          </Button>
        </form>
        <p className="text-center text-sm text-gray-600 mt-4">
          Already have an account? <Link to="/login" className="text-blue-600 hover:underline">Sign In</Link>
        </p>
      </div>
    </div>
  );
}
"""

    def _use_realtime_hook(self):
        return """
import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';

export function useRealtime(events: string[], onEvent?: (type: string, payload: any) => void) {
  const queryClient = useQueryClient();

  useEffect(() => {
    const token = localStorage.getItem('token');
    const wsUrl = `ws://${window.location.hostname}:8000/ws/realtime${token ? `?token=${token}` : ''}`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (events.includes(message.type)) {
          const model = message.type.split('.')[0];
          queryClient.invalidateQueries({ queryKey: [model] });
          onEvent?.(message.type, message.payload);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message', err);
      }
    };

    const interval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);

    return () => {
      clearInterval(interval);
      ws.close();
    };
  }, [events, onEvent, queryClient]);
}
"""

    def _revenue_chart_component(self):
        return """
import { useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface ChartProps {
  data?: { date: string; value: number }[];
  title?: string;
}

export function RevenueChart({ data = [], title = "Analytics Overview" }: ChartProps) {
  const chartData = useMemo(() => data.length ? data : [
    { date: '2026-01-01', value: 1200 },
    { date: '2026-01-02', value: 1900 },
    { date: '2026-01-03', value: 1500 },
    { date: '2026-01-04', value: 2400 },
    { date: '2026-01-05', value: 3100 },
  ], [data]);

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={false} activeDot={{ r: 6 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
"""

