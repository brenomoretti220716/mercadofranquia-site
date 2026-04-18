'use client'

import NotificationButton from '@/src/components/notifications/NotificationButton'
import { Payload } from '@/src/schemas/auth/auth'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import { AdminDesktopActions } from './admin/AdminDesktopActions'
import { FranchisorDesktopActions } from './franchisor/FranchisorDesktopActions'
import { MinimalDesktopNav } from './public/MinimalDesktopNav'

function UserAvatarIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  )
}

export type HeaderVariant = 'public' | 'admin' | 'franchisor' | 'minimal'

type HeaderRightActionsProps =
  | { variant: 'minimal'; darkMode?: boolean }
  | {
      payload: Payload
      variant: 'public'
      darkMode?: boolean
      isAuthenticated: boolean
      dropdownRef: React.RefObject<HTMLDivElement | null>
      isDropdownOpen: boolean
      onDropdownToggle: () => void
    }
  | {
      payload: Payload
      variant: 'admin'
      darkMode?: boolean
      profileDropdownRef: React.RefObject<HTMLDivElement | null>
      isProfileDropdown: boolean
      setIsProfileDropdown: React.Dispatch<React.SetStateAction<boolean>>
    }
  | {
      payload: Payload
      variant: 'franchisor'
      darkMode?: boolean
      profileDropdownRef: React.RefObject<HTMLDivElement | null>
      isProfileDropdown: boolean
      setIsProfileDropdown: React.Dispatch<React.SetStateAction<boolean>>
    }

/**
 * Optional right-side block (login/cadastrar, user menu, etc.).
 */
export function HeaderRightActions(props: HeaderRightActionsProps) {
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  if (props.variant === 'minimal') {
    return <MinimalDesktopNav darkMode={props.darkMode} />
  }

  if (props.variant === 'public') {
    const isLoggedIn = props.isAuthenticated
    const textColor = props.darkMode ? 'text-white' : 'text-[#171726]'
    return (
      <>
        {/* Mobile right actions */}
        <div className="flex md:hidden items-center gap-1">
          {!isLoggedIn && (
            <Link href="/login">
              <button className="px-3.5 py-1.5 rounded text-[13px] font-medium text-white border border-white/60 hover:border-white transition-colors cursor-pointer">
                Login
              </button>
            </Link>
          )}
          {isLoggedIn && (
            <>
              <NotificationButton iconColor="#E25E3E" iconSize={22} />
              <Link
                href="/perfil"
                className={`p-2 ${textColor}`}
                aria-label="Perfil"
              >
                <UserAvatarIcon />
              </Link>
            </>
          )}
        </div>

        {/* Desktop right actions */}
        <div className="hidden md:flex items-center gap-2">
          {!mounted ? (
            <div
              style={{ visibility: 'hidden', width: '200px' }}
              aria-hidden="true"
            />
          ) : (
            <>
              {!isLoggedIn && (
                <>
                  <Link href="/login">
                    <button
                      className={`px-4 py-2 rounded-full text-sm font-medium transition-colors whitespace-nowrap ${textColor} hover:text-primary cursor-pointer`}
                    >
                      Login
                    </button>
                  </Link>
                  <Link href="/cadastro">
                    <button className="bg-primary hover:bg-coral-dark text-white rounded-md px-5 py-2 text-sm font-medium transition-colors whitespace-nowrap cursor-pointer ml-2">
                      Cadastrar Franquia
                    </button>
                  </Link>
                </>
              )}
              {isLoggedIn && (
                <>
                  <NotificationButton iconColor="#E25E3E" iconSize={22} />
                  <Link
                    href="/perfil"
                    className={`p-2 ${textColor}`}
                    aria-label="Perfil"
                  >
                    <UserAvatarIcon />
                  </Link>
                </>
              )}
            </>
          )}
        </div>
      </>
    )
  }

  if (props.variant === 'admin') {
    return (
      <AdminDesktopActions
        profileDropdownRef={props.profileDropdownRef}
        isProfileDropdown={props.isProfileDropdown}
        setIsProfileDropdown={props.setIsProfileDropdown}
      />
    )
  }

  if (props.variant === 'franchisor') {
    return (
      <FranchisorDesktopActions
        profileDropdownRef={props.profileDropdownRef}
        isProfileDropdown={props.isProfileDropdown}
        setIsProfileDropdown={props.setIsProfileDropdown}
        darkMode={props.darkMode}
      />
    )
  }

  return null
}
