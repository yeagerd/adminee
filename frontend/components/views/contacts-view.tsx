import { useIntegrations } from '@/contexts/integrations-context';
import { officeApi } from '@/api';
import type { Contact } from "@/types/api/office";
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { getSession } from 'next-auth/react';
import { RefreshCw } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface ContactsViewProps {
  toolDataLoading?: boolean;
  activeTool?: string;
}

function detectCompanyFromEmail(email?: string): string | undefined {
  if (!email) return undefined;
  const at = email.indexOf('@');
  if (at === -1) return undefined;
  const domain = email.slice(at + 1).toLowerCase();
  const parts = domain.split('.');
  const core = parts.length >= 2 ? parts[parts.length - 2] : parts[0];
  if (!core) return undefined;
  return core.charAt(0).toUpperCase() + core.slice(1);
}

const ContactsView: React.FC<ContactsViewProps> = ({ toolDataLoading = false, activeTool }) => {
  const { loading: integrationsLoading, activeProviders } = useIntegrations();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [companyFilter, setCompanyFilter] = useState('');

  const companies = useMemo(() => {
    const set = new Set<string>();
    contacts.forEach(c => {
      if (c.company) set.add(c.company);
      const primaryEmail = c.primary_email?.email || c.emails?.[0]?.email;
      const derived = detectCompanyFromEmail(primaryEmail);
      if (derived) set.add(derived);
    });
    return Array.from(set).sort();
  }, [contacts]);

  const fetchContacts = useCallback(async (noCache = false) => {
    if (!activeProviders || activeProviders.length === 0) return;
    try {
      const session = await getSession();
      const userId = session?.user?.id;
      if (!userId) throw new Error('No user id found in session');

      const resp = await officeApi.getContacts(activeProviders, 200, search || undefined, companyFilter || undefined, noCache);
      if (resp.success && resp.data) {
        const list = (resp.data.contacts || []) as Contact[];
        setContacts(list);
        setError(null);
      } else {
        setError('Failed to fetch contacts');
      }
    } catch (e: unknown) {
      setError((e && typeof e === 'object' && 'message' in e) ? (e as { message?: string }).message || 'Failed to load contacts' : 'Failed to load contacts');
    }
  }, [activeProviders, search, companyFilter]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await fetchContacts(true);
    } finally {
      setRefreshing(false);
    }
  }, [fetchContacts]);

  useEffect(() => {
    if (toolDataLoading || integrationsLoading) return;
    if (!activeProviders || activeProviders.length === 0) {
      setError('No active integrations found. Connect Google or Microsoft to use Contacts.');
      setContacts([]);
      setLoading(false);
      return;
    }
    if (activeTool !== 'contacts') {
      setLoading(false);
      return;
    }

    let mounted = true;
    setLoading(true);
    (async () => {
      try { await fetchContacts(false); } finally { if (mounted) setLoading(false); }
    })();
    return () => { mounted = false; };
  }, [activeProviders, integrationsLoading, toolDataLoading, activeTool, fetchContacts]);

  const filtered = useMemo(() => contacts, [contacts]);

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b bg-white">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold">Contacts</h1>
          <div className="flex items-center gap-2 ml-4">
            <Input placeholder="Search name or email" value={search} onChange={e => setSearch(e.target.value)} className="w-64" />
            <select value={companyFilter} onChange={(e) => setCompanyFilter(e.target.value)} className="border rounded px-2 py-1 text-sm">
              <option value="">All companies</option>
              {companies.map(c => (<option key={c} value={c}>{c}</option>))}
            </select>
            <Button variant="ghost" size="sm" onClick={handleRefresh} disabled={refreshing || loading} title="Refresh">
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="p-8 text-center text-muted-foreground">Loading…</div>
        ) : error ? (
          <div className="p-8 text-center text-red-500">{error}</div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">No contacts found.</div>
        ) : (
          <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {filtered.map((c) => (
              <div key={c.id} className="bg-white border rounded p-3 shadow-sm">
                <div className="flex items-center gap-3">
                  {c.photo_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={c.photo_url} alt={c.full_name || c.primary_email?.email || ''} className="w-10 h-10 rounded-full object-cover" />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 text-sm">
                      {(c.full_name || c.primary_email?.email || '').slice(0,1).toUpperCase()}
                    </div>
                  )}
                  <div className="min-w-0">
                    <div className="font-medium truncate">{c.full_name || c.primary_email?.email}</div>
                    <div className="text-sm text-gray-500 truncate">{c.primary_email?.email || (c.emails[0]?.email)}</div>
                    {(c.company || detectCompanyFromEmail(c.primary_email?.email || c.emails[0]?.email)) && (
                      <div className="text-xs text-gray-500 truncate">{c.company || detectCompanyFromEmail(c.primary_email?.email || c.emails[0]?.email)}</div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ContactsView;