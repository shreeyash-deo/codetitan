import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { useWorkspace } from '@/hooks/useWorkspace'
import { useToast } from '@/context/ToastContext'
import {
  Shield,
  Cpu,
  Save,
  Check,
  CreditCard,
  Download,
  Building,
  Globe,
  Mail,
  Users,
  Copy,
  FileText,
  CheckCircle2,
  ExternalLink,
  Sparkles,
  Zap,
  ArrowUpRight,
} from 'lucide-react'

type SettingsTab = 'general' | 'compliance' | 'billing' | 'integrations' | 'team'

interface InvoiceRecord {
  id: string
  date: string
  amount: string
  status: 'Paid' | 'Processing'
  period: string
}

export const SettingsPage: React.FC = () => {
  const { currentWorkspace } = useWorkspace()
  const { success, info } = useToast()

  const [activeTab, setActiveTab] = useState<SettingsTab>('general')
  const [sensitivity, setSensitivity] = useState(85)
  const [autoReject, setAutoReject] = useState(true)
  const [slackAlerts, setSlackAlerts] = useState(true)
  const [strictnessLevel, setStrictnessLevel] = useState<'permissive' | 'standard' | 'strict'>('standard')
  const [saved, setSaved] = useState(false)
  const [copiedKey, setCopiedKey] = useState(false)

  // Webhook and integration states
  const [integrations, setIntegrations] = useState([
    { id: 'figma', name: 'Figma Brand Plugin', desc: 'Scan design frames directly during handoff in Figma', connected: true, category: 'Design' },
    { id: 'contentful', name: 'Contentful CMS Gatekeeper', desc: 'Pre-publish compliance webhook check for web copy', connected: true, category: 'CMS' },
    { id: 'slack', name: 'Slack Compliance Sentinel', desc: 'Real-time alert dispatch to #brand-governance channel', connected: true, category: 'Alerts' },
    { id: 'github', name: 'GitHub Action Sentinel', desc: 'Automated CI/CD pull request reviewer for marketing docs', connected: false, category: 'Engineering' },
    { id: 'adobe', name: 'Adobe Creative Cloud Connector', desc: 'Live vector asset validation in Illustrator and InDesign', connected: false, category: 'Design' },
  ])

  // Invoices list
  const invoices: InvoiceRecord[] = [
    { id: 'INV-2026-1104', date: 'Nov 1, 2026', period: 'Nov 1 - Dec 1, 2026', amount: '$499.00', status: 'Paid' },
    { id: 'INV-2026-1002', date: 'Oct 1, 2026', period: 'Oct 1 - Nov 1, 2026', amount: '$499.00', status: 'Paid' },
    { id: 'INV-2026-0901', date: 'Sep 1, 2026', period: 'Sep 1 - Oct 1, 2026', amount: '$499.00', status: 'Paid' },
    { id: 'INV-2026-0803', date: 'Aug 1, 2026', period: 'Aug 1 - Sep 1, 2026', amount: '$499.00', status: 'Paid' },
  ]

  const handleSave = () => {
    setSaved(true)
    success('Workspace compliance parameters saved to cloud config.', 'Settings Updated')
    setTimeout(() => setSaved(false), 2000)
  }

  const handleToggleIntegration = (id: string, name: string, isConnected: boolean) => {
    setIntegrations(prev =>
      prev.map(item => (item.id === id ? { ...item, connected: !isConnected } : item))
    )
    if (!isConnected) {
      success(`Authorization handshake initiated for "${name}".`, 'Integration Connected')
    } else {
      info(`Integration "${name}" disconnected.`, 'Integration Removed')
    }
  }

  const handleCopyApiKey = () => {
    navigator.clipboard.writeText('bsh_live_948f29d8a11e405b82c7a68')
    setCopiedKey(true)
    success('Workspace API Token copied to clipboard.', 'Copied')
    setTimeout(() => setCopiedKey(false), 2000)
  }

  const handleDownloadInvoice = (invId: string) => {
    success(`Invoice ${invId} downloaded as PDF receipt.`, 'Invoice Downloaded')
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="space-y-6 max-w-5xl"
    >
      <PageHeader
        title="Settings & Policies"
        description="Configure workspace identity, AI compliance engine parameters, billing plans, and ecosystem integrations."
        actions={
          <Button
            variant="primaryBlue"
            size="sm"
            className="gap-1.5"
            onClick={handleSave}
          >
            {saved ? <Check className="w-3.5 h-3.5" /> : <Save className="w-3.5 h-3.5" />}
            <span>{saved ? 'Saved' : 'Save Changes'}</span>
          </Button>
        }
      />

      {/* Settings Navigation Tabs */}
      <div className="flex items-center gap-1.5 border-b border-border pb-1 overflow-x-auto text-xs font-medium">
        {[
          { id: 'general', label: 'General & Identity' },
          { id: 'compliance', label: 'Compliance Engine' },
          { id: 'billing', label: 'Plans & Billing' },
          { id: 'integrations', label: 'Integrations & Webhooks' },
          { id: 'team', label: 'Team Roles & Access' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as SettingsTab)}
            className={`px-3 py-2 rounded-t-md transition-all shrink-0 ${
              activeTab === tab.id
                ? 'border-b-2 border-blue-600 font-semibold text-blue-600 bg-blue-50/40'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/60'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* TAB 1: GENERAL & IDENTITY */}
      {activeTab === 'general' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Building className="w-4 h-4 text-blue-600" />
                <span>Workspace Profile</span>
              </CardTitle>
              <CardDescription className="text-xs">
                General brand identity and root corporate configuration for this environment.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-700">Workspace Brand Name</label>
                  <Input defaultValue={currentWorkspace?.name || ''} />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-700">Organization Slug</label>
                  <Input defaultValue={currentWorkspace?.slug || ''} />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-700">Primary Brand Domain</label>
                  <div className="relative">
                    <Globe className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-400" />
                    <Input defaultValue="novapay.io" className="pl-9" />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-700">Governance Lead Email</label>
                  <div className="relative">
                    <Mail className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-400" />
                    <Input defaultValue="sarah.chen@novapay.io" className="pl-9" />
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-border flex items-center justify-between text-xs text-slate-500">
                <span>Active Subscription Tier: <strong className="text-slate-800">{currentWorkspace?.plan || 'Enterprise'}</strong></span>
                <Badge variant="blue">Enterprise SLA Active</Badge>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Data Retention & Audit Logging</CardTitle>
              <CardDescription className="text-xs">
                Configure immutable audit log preservation schedules for legal discovery and financial compliance.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-slate-800">Immutable Audit Trail Storage</div>
                  <div className="text-[11px] text-slate-500">Retain all submitted drafts, AI suggestions, and human sign-offs.</div>
                </div>
                <select className="h-8 rounded-md border border-input bg-white px-2.5 text-xs text-slate-700">
                  <option value="365">1 Year Retention (Compliant)</option>
                  <option value="730">2 Years Retention</option>
                  <option value="1825">5 Years (Statutory Financial)</option>
                  <option value="unlimited">Indefinite Archive</option>
                </select>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* TAB 2: COMPLIANCE ENGINE */}
      {activeTab === 'compliance' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-blue-600" />
                <CardTitle className="text-base">AI Inspection Parameters</CardTitle>
              </div>
              <CardDescription className="text-xs">
                Calibrate strictness thresholds for automated flagging and human sign-off triggers.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-700">
                    Minimum Approval Pass Threshold ({sensitivity}%)
                  </label>
                  <span className="text-xs font-mono font-bold text-blue-600">{sensitivity}%</span>
                </div>
                <input
                  type="range"
                  min="60"
                  max="99"
                  value={sensitivity}
                  onChange={(e) => setSensitivity(Number(e.target.value))}
                  className="w-full accent-blue-600 cursor-pointer"
                />
                <p className="text-[11px] text-slate-400">
                  Content scoring below {sensitivity}% automatically requires manual remediation by an authorized Brand Lead.
                </p>
              </div>

              <div className="pt-2 border-t border-border flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-slate-800">Inspection Strictness Mode</div>
                  <div className="text-[11px] text-slate-500">Determines tone tolerance and terminology boundary rigidity.</div>
                </div>
                <div className="flex items-center gap-1.5">
                  {(['permissive', 'standard', 'strict'] as const).map((level) => (
                    <button
                      key={level}
                      type="button"
                      onClick={() => setStrictnessLevel(level)}
                      className={`px-3 py-1 rounded-md text-xs capitalize font-medium transition-colors ${
                        strictnessLevel === level
                          ? 'bg-slate-900 text-white shadow-xs'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      {level}
                    </button>
                  ))}
                </div>
              </div>

              <div className="pt-2 border-t border-border flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-slate-800">Auto-reject statutory disclaimer violations</div>
                  <div className="text-[11px] text-slate-500">
                    Immediately reject creative assets omitting mandatory regulatory footers.
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={autoReject}
                  onChange={(e) => setAutoReject(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                />
              </div>

              <div className="pt-2 border-t border-border flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-slate-800">Broadcast violations to Slack</div>
                  <div className="text-[11px] text-slate-500">
                    Immediately send critical audit incidents to #brand-governance.
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={slackAlerts}
                  onChange={(e) => setSlackAlerts(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* TAB 3: PLANS & BILLING */}
      {activeTab === 'billing' && (
        <div className="space-y-6">
          {/* Current Subscription Card */}
          <Card className="border-blue-200 bg-blue-50/20">
            <CardHeader className="pb-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-lg font-bold text-slate-900">Enterprise Governance</CardTitle>
                    <Badge variant="blue" className="text-[10px]">Active Plan</Badge>
                  </div>
                  <CardDescription className="text-xs text-slate-600 mt-1">
                    Multi-tier brand governance, unlimited approved rules, custom API access, and 99.9% uptime SLA.
                  </CardDescription>
                </div>
                <div className="text-left sm:text-right shrink-0">
                  <div className="text-2xl font-extrabold text-slate-900">$499<span className="text-xs text-slate-500 font-normal"> / month</span></div>
                  <div className="text-[11px] text-emerald-700 font-medium">Billed annually ($4,790/yr • 20% savings)</div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-2 border-t border-blue-200/60">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between text-xs text-slate-600 gap-2">
                <span>Next automated renewal date: <strong className="text-slate-800">December 1, 2026</strong></span>
                <span className="text-[11px] text-slate-500">Payment auto-charged to primary corporate card</span>
              </div>
            </CardContent>
          </Card>

          {/* Usage Quotas */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Current Billing Cycle Usage</CardTitle>
              <CardDescription className="text-xs">
                Usage metrics for Nov 1 – Dec 1, 2026. Quotas reset automatically at the end of the billing period.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-3.5 rounded-lg border border-border bg-slate-50/50 space-y-1.5">
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>AI Audits</span>
                    <span className="font-semibold text-slate-800">124 / 500</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                    <div className="h-full bg-blue-600 rounded-full" style={{ width: '24.8%' }} />
                  </div>
                  <div className="text-[10px] text-slate-400">24.8% consumed</div>
                </div>

                <div className="p-3.5 rounded-lg border border-border bg-slate-50/50 space-y-1.5">
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>Active Guidelines</span>
                    <span className="font-semibold text-slate-800">48 / ∞</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                    <div className="h-full bg-emerald-600 rounded-full" style={{ width: '10%' }} />
                  </div>
                  <div className="text-[10px] text-slate-400">Unlimited on Enterprise</div>
                </div>

                <div className="p-3.5 rounded-lg border border-border bg-slate-50/50 space-y-1.5">
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>Team Seats</span>
                    <span className="font-semibold text-slate-800">8 / 15</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                    <div className="h-full bg-blue-600 rounded-full" style={{ width: '53.3%' }} />
                  </div>
                  <div className="text-[10px] text-slate-400">7 seats available</div>
                </div>

                <div className="p-3.5 rounded-lg border border-border bg-slate-50/50 space-y-1.5">
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>Integrations</span>
                    <span className="font-semibold text-slate-800">3 / 5</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                    <div className="h-full bg-blue-600 rounded-full" style={{ width: '60%' }} />
                  </div>
                  <div className="text-[10px] text-slate-400">2 slots available</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Transparent Plan Comparison Grid */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-slate-900">Available Plans & Tier Upgrades</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Starter */}
              <div className="p-4 rounded-xl border border-border bg-white space-y-3 flex flex-col justify-between">
                <div>
                  <div className="text-sm font-bold text-slate-900">Starter</div>
                  <div className="text-xs text-slate-500 mt-0.5">For single-brand startups</div>
                  <div className="text-xl font-extrabold text-slate-900 mt-2">$99<span className="text-xs font-normal text-slate-500"> / mo</span></div>
                  <ul className="mt-3 space-y-1.5 text-xs text-slate-600">
                    <li className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-blue-600 shrink-0" /> 1 Brand Workspace</li>
                    <li className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-blue-600 shrink-0" /> 50 AI audits / month</li>
                    <li className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-blue-600 shrink-0" /> Standard terminology check</li>
                    <li className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-blue-600 shrink-0" /> Email support</li>
                  </ul>
                </div>
                <Button variant="outline" size="sm" className="w-full text-xs" onClick={() => info('You are currently on Enterprise with superior coverage.', 'Plan Info')}>
                  Downgrade
                </Button>
              </div>

              {/* Pro */}
              <div className="p-4 rounded-xl border border-border bg-white space-y-3 flex flex-col justify-between">
                <div>
                  <div className="text-sm font-bold text-slate-900">Professional</div>
                  <div className="text-xs text-slate-500 mt-0.5">For growing marketing teams</div>
                  <div className="text-xl font-extrabold text-slate-900 mt-2">$249<span className="text-xs font-normal text-slate-500"> / mo</span></div>
                  <ul className="mt-3 space-y-1.5 text-xs text-slate-600">
                    <li className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-blue-600 shrink-0" /> Up to 3 Brand Workspaces</li>
                    <li className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-blue-600 shrink-0" /> 200 AI audits / month</li>
                    <li className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-blue-600 shrink-0" /> Custom Tone Calibration</li>
                    <li className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-blue-600 shrink-0" /> Slack & Figma integrations</li>
                  </ul>
                </div>
                <Button variant="outline" size="sm" className="w-full text-xs" onClick={() => info('You are currently on Enterprise with superior coverage.', 'Plan Info')}>
                  Select Plan
                </Button>
              </div>

              {/* Enterprise (Current) */}
              <div className="p-4 rounded-xl border-2 border-blue-600 bg-white space-y-3 flex flex-col justify-between shadow-xs relative">
                <Badge variant="blue" className="absolute -top-2.5 right-4 text-[9px] uppercase tracking-wider">
                  Current Active Plan
                </Badge>
                <div>
                  <div className="text-sm font-bold text-slate-900">Enterprise</div>
                  <div className="text-xs text-slate-500 mt-0.5">For regulated enterprises & fintechs</div>
                  <div className="text-xl font-extrabold text-slate-900 mt-2">$499<span className="text-xs font-normal text-slate-500"> / mo</span></div>
                  <ul className="mt-3 space-y-1.5 text-xs text-slate-600">
                    <li className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-blue-600 shrink-0" /> Unlimited Brand Workspaces</li>
                    <li className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-blue-600 shrink-0" /> 500+ Audits & Dedicated Throughput</li>
                    <li className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-blue-600 shrink-0" /> Multi-tier Human Sign-off Workflows</li>
                    <li className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-blue-600 shrink-0" /> 99.9% SLA & Dedicated Support</li>
                  </ul>
                </div>
                <Button variant="primaryBlue" size="sm" className="w-full text-xs" disabled>
                  Current Active Tier
                </Button>
              </div>
            </div>
          </div>

          {/* Payment Method & Billing Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <CreditCard className="w-4 h-4 text-slate-600" />
                  <span>Payment Method</span>
                </CardTitle>
                <CardDescription className="text-xs">Primary card used for recurring charges.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="p-3 rounded-lg border border-border flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-6 rounded bg-slate-900 text-white font-mono text-[10px] font-bold flex items-center justify-center">
                      VISA
                    </div>
                    <div>
                      <div className="text-xs font-semibold text-slate-800">Visa ending in 4242</div>
                      <div className="text-[11px] text-slate-500">Expires 08/2029</div>
                    </div>
                  </div>
                  <Button variant="outline" size="sm" className="text-xs" onClick={() => info('Billing portal opened in secure session.', 'Billing Session')}>
                    Update
                  </Button>
                </div>
                <div className="text-[11px] text-slate-500">
                  Billing Contact: <strong className="text-slate-700">billing@novapay.io</strong>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Billing Address & VAT</CardTitle>
                <CardDescription className="text-xs">Corporate tax and legal invoice recipient.</CardDescription>
              </CardHeader>
              <CardContent className="text-xs text-slate-600 space-y-1">
                <p className="font-semibold text-slate-800">NovaPay Technologies, Inc.</p>
                <p>100 Montgomery Street, Suite 1400</p>
                <p>San Francisco, CA 94104, United States</p>
                <p className="text-slate-400 text-[11px] pt-1">VAT / Tax ID: US-EIN-94-2849102</p>
              </CardContent>
            </Card>
          </div>

          {/* Invoices History Table */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Invoice History</CardTitle>
              <CardDescription className="text-xs">Download official PDF receipts and statements.</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-slate-50/70 border-b border-border/80 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                    <tr>
                      <th className="px-4 py-3">Invoice</th>
                      <th className="px-4 py-3">Billing Period</th>
                      <th className="px-4 py-3">Date</th>
                      <th className="px-4 py-3">Amount</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 text-right">Receipt</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {invoices.map(inv => (
                      <tr key={inv.id} className="hover:bg-slate-50/50 transition-colors">
                        <td className="px-4 py-3 font-mono font-medium text-slate-900">{inv.id}</td>
                        <td className="px-4 py-3 text-slate-600">{inv.period}</td>
                        <td className="px-4 py-3 text-slate-500">{inv.date}</td>
                        <td className="px-4 py-3 font-semibold text-slate-800">{inv.amount}</td>
                        <td className="px-4 py-3">
                          <Badge variant="success" className="text-[10px] gap-1">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            {inv.status}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            type="button"
                            onClick={() => handleDownloadInvoice(inv.id)}
                            className="text-blue-600 hover:text-blue-700 font-medium inline-flex items-center gap-1"
                          >
                            <Download className="w-3 h-3" />
                            <span>PDF</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* TAB 4: INTEGRATIONS & WEBHOOKS */}
      {activeTab === 'integrations' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Connected Ecosystem</CardTitle>
              <CardDescription className="text-xs">
                Sync BrandShield directly into your design, CMS, and deployment pipelines.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {integrations.map((item) => (
                <div
                  key={item.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-lg border border-border bg-slate-50/50 gap-3"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-slate-800">{item.name}</span>
                      <Badge variant="neutral" className="text-[9px] uppercase">{item.category}</Badge>
                      {item.connected && (
                        <span className="inline-flex items-center gap-1 text-[10px] text-emerald-700 font-medium">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                          Streaming
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-500">{item.desc}</div>
                  </div>
                  <Button
                    variant={item.connected ? 'outline' : 'primaryBlue'}
                    size="sm"
                    className="text-xs self-start sm:self-auto"
                    onClick={() => handleToggleIntegration(item.id, item.name, item.connected)}
                  >
                    {item.connected ? 'Disconnect' : 'Connect'}
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Webhook Endpoint & API Keys */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Custom Webhook Dispatcher</CardTitle>
              <CardDescription className="text-xs">
                Broadcast real-time JSON audit events to your custom backend or message broker.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700">Webhook Destination URL</label>
                <div className="flex gap-2">
                  <Input defaultValue="https://api.novapay.io/webhooks/brand-governance" />
                  <Button
                    variant="outline"
                    size="sm"
                    className="shrink-0 text-xs"
                    onClick={() => success('Sample test payload dispatched with HTTP 200 OK.', 'Test Webhook Fired')}
                  >
                    Send Test Ping
                  </Button>
                </div>
              </div>

              <div className="pt-2 border-t border-border space-y-1.5">
                <label className="text-xs font-semibold text-slate-700">Production API Signing Key</label>
                <div className="flex items-center gap-2">
                  <Input readOnly value="bsh_live_948f29d8a11e405b82c7a68" className="font-mono text-xs bg-slate-50" />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCopyApiKey}
                    className="shrink-0 gap-1 text-xs"
                  >
                    {copiedKey ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedKey ? 'Copied' : 'Copy'}</span>
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* TAB 5: TEAM ROLES & ACCESS */}
      {activeTab === 'team' && (
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Users className="w-4 h-4 text-blue-600" />
                    <span>Workspace Governance Roster</span>
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Assigned roles, permissions, and sign-off authority for NovaPay.
                  </CardDescription>
                </div>
                <Button
                  variant="primaryBlue"
                  size="sm"
                  className="text-xs"
                  onClick={() => info('Invite link generated and copied to clipboard.', 'Invite Member')}
                >
                  Invite Colleague
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-slate-50/70 border-b border-border/80 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                    <tr>
                      <th className="px-4 py-3">Member</th>
                      <th className="px-4 py-3">Role</th>
                      <th className="px-4 py-3">Sign-off Authority</th>
                      <th className="px-4 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {[
                      { name: 'Sarah Chen', email: 'sarah.chen@novapay.io', role: 'Brand Lead', auth: 'Tier 3 (Final Authorization)', avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop&q=80' },
                      { name: 'Marcus Vance', email: 'marcus@novapay.io', role: 'Senior Compliance Reviewer', auth: 'Tier 2 (Legal & Claims)', avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80' },
                      { name: 'Elena Rostova', email: 'elena@novapay.io', role: 'Creative Director', auth: 'Tier 1 (Visual & Identity)', avatar: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?w=100&auto=format&fit=crop&q=80' },
                      { name: 'David Kim', email: 'david@novapay.io', role: 'Product Marketing Manager', auth: 'Submit & Remediate', avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop&q=80' },
                    ].map(member => (
                      <tr key={member.email} className="hover:bg-slate-50/50 transition-colors">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2.5">
                            <Avatar className="w-7 h-7">
                              <AvatarImage src={member.avatar} alt={member.name} />
                              <AvatarFallback className="text-[10px]">{member.name.slice(0, 2)}</AvatarFallback>
                            </Avatar>
                            <div>
                              <div className="font-semibold text-slate-900">{member.name}</div>
                              <div className="text-[11px] text-slate-400">{member.email}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 font-medium text-slate-700">{member.role}</td>
                        <td className="px-4 py-3 font-mono text-[11px] text-blue-700">{member.auth}</td>
                        <td className="px-4 py-3">
                          <Badge variant="success" className="text-[9px]">Active</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </motion.div>
  )
}
