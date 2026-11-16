import React, { useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import {
  Shield,
  Lock,
  Mail,
  User,
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Loader2,
  Building2,
  Users,
  Key,
  Copy,
  Check,
  Sparkles,
  Info,
  Crown,
  FileCheck,
  UserCheck,
} from 'lucide-react'

interface DemoAccount {
  role: 'Admin' | 'Reviewer' | 'Employee'
  email: string
  password: string
  title: string
  description: string
  badgeColor: string
  Icon: React.ComponentType<{ className?: string }>
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    role: 'Admin',
    email: 'admin_verify_rc_v2@test.com',
    password: 'Pass123!',
    title: 'Workspace Administrator',
    description: 'Full workspace governance, guidelines ingestion, rule approvals & settings',
    badgeColor: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    Icon: Crown,
  },
  {
    role: 'Reviewer',
    email: 'rev_verify_rc_v2@test.com',
    password: 'Pass123!',
    title: 'Compliance Reviewer',
    description: 'Audits submissions, inspects AI findings, requests revisions & issues sign-offs',
    badgeColor: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    Icon: FileCheck,
  },
  {
    role: 'Employee',
    email: 'emp_verify_rc_v2@test.com',
    password: 'Pass123!',
    title: 'Content Creator',
    description: 'Drafts copy, runs real-time AI scans, applies fixes & submits for sign-off',
    badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    Icon: UserCheck,
  },
]

export const AuthPage: React.FC = () => {
  const { login, register } = useAuth()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [regPath, setRegPath] = useState<'create' | 'join'>('create')

  // Form State
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [orgId, setOrgId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Demo Credentials Interaction State
  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  const [autoFilledRole, setAutoFilledRole] = useState<string | null>(null)

  const copyToClipboard = async (text: string, key: string) => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text)
      } else {
        const textArea = document.createElement('textarea')
        textArea.value = text
        textArea.style.position = 'fixed'
        textArea.style.opacity = '0'
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
      }
      setCopiedKey(key)
      setTimeout(() => {
        setCopiedKey((prev) => (prev === key ? null : prev))
      }, 2000)
    } catch (err) {
      console.error('Failed to copy to clipboard', err)
    }
  }

  const handleAutoFill = (account: DemoAccount) => {
    setEmail(account.email)
    setPassword(account.password)
    setMode('login')
    setError(null)
    setAutoFilledRole(account.role)
    setTimeout(() => {
      setAutoFilledRole((prev) => (prev === account.role ? null : prev))
    }, 2500)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      if (mode === 'login') {
        if (!email.trim() || !password) {
          throw new Error('Please enter both your email address and password.')
        }
        await login({ email: email.trim(), password })
      } else {
        if (!name.trim()) {
          throw new Error('Please enter your full name.')
        }
        if (!email.trim() || !email.includes('@')) {
          throw new Error('Please enter a valid email address.')
        }
        if (password.length < 6) {
          throw new Error('Password must be at least 6 characters long.')
        }

        if (regPath === 'join') {
          const cleanOrgId = orgId.trim().toUpperCase()
          if (!cleanOrgId) {
            throw new Error('Please enter the Organisation ID you wish to join (e.g. ORG-XXXXXXXX).')
          }
          await register({
            name: name.trim(),
            email: email.trim(),
            password,
            org_id: cleanOrgId,
          })
        } else {
          await register({
            name: name.trim(),
            email: email.trim(),
            password,
          })
        }
      }
    } catch (err: any) {
      setError(err?.detail || err?.message || 'Authentication failed. Please verify your credentials.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen w-screen bg-[#070C14] text-slate-100 flex items-center justify-center p-4 sm:p-6 lg:p-8 relative overflow-y-auto select-none">
      {/* Background ambient lighting */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-blue-600/10 blur-[130px] rounded-full pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/3 w-[400px] h-[300px] bg-indigo-600/10 blur-[120px] rounded-full pointer-events-none" />

      <div className="w-full max-w-md lg:max-w-4xl z-10 relative py-8">
        <div className="lg:grid lg:grid-cols-2 lg:gap-8 lg:items-start space-y-6 lg:space-y-0">
          {/* Column 1: Header + Auth Form */}
          <div>
            {/* Header Logo */}
            <div className="flex flex-col items-center mb-6 text-center">
              <div className="flex items-center justify-center p-3 rounded-2xl bg-gradient-to-b from-blue-500/20 to-blue-600/5 border border-blue-500/20 shadow-lg shadow-blue-500/10 mb-4">
                <Shield className="w-8 h-8 text-blue-400" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                BrandShield{' '}
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 font-medium">
                  Enterprise
                </span>
              </h1>
              <p className="text-xs text-slate-400 mt-1 max-w-xs">
                AI-Powered Brand Governance & Real-Time Content Compliance
              </p>
            </div>

            {/* Auth Card */}
            <div className="bg-[#0D1524]/90 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-2xl shadow-black/60">
              {/* Mode Switcher Tabs */}
              <div className="flex p-1 bg-slate-900/90 rounded-lg border border-slate-800 mb-6">
                <button
                  type="button"
                  onClick={() => {
                    setMode('login')
                    setError(null)
                  }}
                  className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${
                    mode === 'login'
                      ? 'bg-blue-600 text-white shadow-xs'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Sign In
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMode('register')
                    setError(null)
                  }}
                  className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${
                    mode === 'register'
                      ? 'bg-blue-600 text-white shadow-xs'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Create Account
                </button>
              </div>

              {/* Registration Path Sub-Tabs (Create vs Join) */}
              {mode === 'register' && (
                <div className="grid grid-cols-2 gap-2 mb-5">
                  <button
                    type="button"
                    onClick={() => setRegPath('create')}
                    className={`p-2.5 rounded-lg border text-left transition-all cursor-pointer ${
                      regPath === 'create'
                        ? 'bg-blue-600/10 border-blue-500/50 text-white'
                        : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 mb-1 font-semibold text-xs">
                      <Building2
                        className={`w-3.5 h-3.5 ${regPath === 'create' ? 'text-blue-400' : 'text-slate-400'}`}
                      />
                      <span>Create New Org</span>
                    </div>
                    <div className="text-[11px] text-slate-400 leading-tight">Start fresh as an Admin</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setRegPath('join')}
                    className={`p-2.5 rounded-lg border text-left transition-all cursor-pointer ${
                      regPath === 'join'
                        ? 'bg-blue-600/10 border-blue-500/50 text-white'
                        : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 mb-1 font-semibold text-xs">
                      <Users
                        className={`w-3.5 h-3.5 ${regPath === 'join' ? 'text-blue-400' : 'text-slate-400'}`}
                      />
                      <span>Join Existing Org</span>
                    </div>
                    <div className="text-[11px] text-slate-400 leading-tight">Join via ORG ID code</div>
                  </button>
                </div>
              )}

              {/* Error Alert */}
              {error && (
                <div className="mb-5 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5 animate-in fade-in duration-150">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
                  <div className="flex-1 leading-relaxed">{error}</div>
                </div>
              )}

              {/* Form */}
              <form onSubmit={handleSubmit} className="space-y-4">
                {mode === 'register' && (
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1.5">
                      Full Name
                    </label>
                    <div className="relative">
                      <User className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        required
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="e.g. Sarah Chen"
                        className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-slate-900/80 border border-slate-700/80 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                      />
                    </div>
                  </div>
                )}

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Work Email Address
                  </label>
                  <div className="relative">
                    <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="name@company.com"
                      className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-slate-900/80 border border-slate-700/80 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Password
                  </label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-slate-900/80 border border-slate-700/80 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                    />
                  </div>
                </div>

                {mode === 'register' && regPath === 'join' && (
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="block text-xs font-medium text-slate-300">
                        Organisation ID
                      </label>
                      <span className="text-[11px] text-slate-400 font-mono">Format: ORG-XXXXXXXX</span>
                    </div>
                    <div className="relative">
                      <Building2 className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        required
                        value={orgId}
                        onChange={(e) => setOrgId(e.target.value.toUpperCase())}
                        placeholder="e.g. ORG-A1B2C3D4"
                        className="w-full pl-9 pr-3 py-2 text-xs font-mono uppercase tracking-wider rounded-lg bg-slate-900/80 border border-slate-700/80 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                      />
                    </div>
                  </div>
                )}

                {mode === 'register' && regPath === 'create' && (
                  <div className="p-2.5 rounded-lg bg-blue-950/30 border border-blue-900/40 text-[11px] text-blue-300/90 flex items-start gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-400 shrink-0 mt-0.5" />
                    <span>
                      Creating an organisation automatically establishes you as its primary{' '}
                      <strong className="text-white">Admin</strong>.
                    </span>
                  </div>
                )}

                {mode === 'register' && regPath === 'join' && (
                  <div className="p-2.5 rounded-lg bg-amber-950/30 border border-amber-900/40 text-[11px] text-amber-300/90 flex items-start gap-2">
                    <Users className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                    <span>
                      Joining an organisation submits a request for the{' '}
                      <strong className="text-white">Employee</strong> role in{' '}
                      <strong className="text-white">Pending Approval</strong> status. An Admin must
                      approve your access before you can view workspaces.
                    </span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full mt-2 py-2.5 px-4 rounded-lg bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white text-xs font-semibold shadow-lg shadow-blue-600/20 flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Authenticating...</span>
                    </>
                  ) : (
                    <>
                      <span>
                        {mode === 'login'
                          ? 'Sign In to BrandShield'
                          : regPath === 'join'
                          ? 'Submit Request & Join'
                          : 'Create Account & Sign In'}
                      </span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>

          {/* Column 2: Demo Credentials Card + Security Badge */}
          <div className="space-y-4">
            {/* Demo Credentials Section */}
            <div className="bg-[#0D1524]/90 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-6 shadow-2xl shadow-black/60">
              {/* Section Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-xl bg-gradient-to-b from-blue-500/20 to-blue-600/5 border border-blue-500/20 text-blue-400 shadow-sm shadow-blue-500/10">
                    <Key className="w-4 h-4" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                      Demo Credentials
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Active
                      </span>
                    </h2>
                    <p className="text-[11px] text-slate-400">
                      Pre-configured role accounts for evaluation
                    </p>
                  </div>
                </div>
              </div>

              {/* Demo Accounts List */}
              <div className="space-y-3">
                {DEMO_ACCOUNTS.map((account) => {
                  const isAutoFilled = autoFilledRole === account.role
                  const isEmailCopied = copiedKey === `${account.role}-email`
                  const isPasswordCopied = copiedKey === `${account.role}-password`
                  const RoleIcon = account.Icon

                  return (
                    <div
                      key={account.role}
                      onClick={() => handleAutoFill(account)}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer relative group ${
                        isAutoFilled
                          ? 'bg-blue-950/30 border-blue-500/50 shadow-md shadow-blue-500/10'
                          : 'bg-slate-900/60 border-slate-800/80 hover:bg-slate-900/90 hover:border-slate-700/80'
                      }`}
                    >
                      {/* Role Header & Auto-fill Action */}
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <div className="flex items-center gap-2">
                          <span
                            className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-semibold border ${account.badgeColor}`}
                          >
                            <RoleIcon className="w-3 h-3" />
                            {account.role}
                          </span>
                          <span className="text-[11px] font-medium text-slate-300">
                            {account.title}
                          </span>
                        </div>

                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleAutoFill(account)
                          }}
                          className={`px-2 py-1 text-[11px] font-medium rounded-md transition-all flex items-center gap-1 cursor-pointer shrink-0 ${
                            isAutoFilled
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : 'bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 border border-blue-500/30 hover:border-blue-500/50'
                          }`}
                        >
                          {isAutoFilled ? (
                            <>
                              <Check className="w-3 h-3 text-emerald-400" />
                              <span>Filled</span>
                            </>
                          ) : (
                            <>
                              <Sparkles className="w-3 h-3" />
                              <span>Auto-fill</span>
                            </>
                          )}
                        </button>
                      </div>

                      {/* Role Description */}
                      <p className="text-[11px] text-slate-400 mb-2.5 leading-snug">
                        {account.description}
                      </p>

                      {/* Credentials Grid */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                        {/* Email */}
                        <div className="flex items-center justify-between p-2 rounded-lg bg-slate-950/60 border border-slate-800/60 font-mono text-[11px]">
                          <div className="truncate mr-1 text-slate-300">
                            <span className="text-slate-500 select-none mr-1.5 font-sans">Email:</span>
                            <span className="select-all">{account.email}</span>
                          </div>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              copyToClipboard(account.email, `${account.role}-email`)
                            }}
                            title="Copy email address"
                            className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors shrink-0 cursor-pointer"
                          >
                            {isEmailCopied ? (
                              <Check className="w-3 h-3 text-emerald-400" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                          </button>
                        </div>

                        {/* Password */}
                        <div className="flex items-center justify-between p-2 rounded-lg bg-slate-950/60 border border-slate-800/60 font-mono text-[11px]">
                          <div className="truncate mr-1 text-slate-300">
                            <span className="text-slate-500 select-none mr-1.5 font-sans">Pass:</span>
                            <span className="select-all">{account.password}</span>
                          </div>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              copyToClipboard(account.password, `${account.role}-password`)
                            }}
                            title="Copy password"
                            className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors shrink-0 cursor-pointer"
                          >
                            {isPasswordCopied ? (
                              <Check className="w-3 h-3 text-emerald-400" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Disclaimer Note */}
              <div className="mt-4 p-3 rounded-xl bg-slate-900/40 border border-slate-800/80 text-[11px] text-slate-400 flex items-start gap-2.5 leading-relaxed">
                <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                <span>Demo accounts are provided for evaluation. Please do not enter personal information.</span>
              </div>
            </div>

            {/* Security badge footer */}
            <div className="text-center text-[11px] text-slate-500 flex items-center justify-center gap-2 pt-2">
              <Shield className="w-3 h-3 text-emerald-500 inline" />
              <span>Multi-tenant tenant isolation & cryptographic JWT RBAC enforced</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
