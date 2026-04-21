'use client'

import { useId } from 'react'

export interface ModeSelectorOption<T extends string> {
  value: T
  label: string
  description?: string
  icon?: React.ReactNode
}

interface ModeSelectorCardProps<T extends string> {
  options: ModeSelectorOption<T>[]
  value: T | null
  onChange: (value: T) => void
  name: string
  disabled?: boolean
  className?: string
}

/**
 * Grupo de cards grandes clicáveis para escolha entre 2-4 opções.
 * Alternativa visual ao radio tradicional — cards têm ícone, título e descrição.
 *
 * Acessibilidade: usa role="radiogroup" + role="radio" + aria-checked.
 * Navegação por teclado: Tab move entre cards, Space/Enter seleciona.
 */
export default function ModeSelectorCard<T extends string>({
  options,
  value,
  onChange,
  name,
  disabled = false,
  className = '',
}: ModeSelectorCardProps<T>) {
  const groupId = useId()

  return (
    <div
      role="radiogroup"
      aria-labelledby={`${groupId}-label`}
      className={`grid gap-3 sm:grid-cols-2 ${className}`}
    >
      <span id={`${groupId}-label`} className="sr-only">
        {name}
      </span>

      {options.map((option) => {
        const isSelected = value === option.value
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={isSelected}
            disabled={disabled}
            onClick={() => onChange(option.value)}
            className={`
              relative flex flex-col items-start gap-2 p-5 rounded-xl border-2 text-left
              transition-all
              focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#E25E3E]/30
              disabled:opacity-50 disabled:cursor-not-allowed
              ${
                isSelected
                  ? 'border-[#E25E3E] bg-[#FFF4F0] shadow-sm'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
              }
            `}
          >
            {/* Indicador visual de seleção no canto superior direito */}
            <div
              className={`
                absolute top-4 right-4 w-5 h-5 rounded-full border-2 flex items-center justify-center
                transition-colors
                ${isSelected ? 'border-[#E25E3E] bg-[#E25E3E]' : 'border-gray-300 bg-white'}
              `}
              aria-hidden="true"
            >
              {isSelected && (
                <svg
                  className="w-3 h-3 text-white"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  strokeWidth={3}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              )}
            </div>

            {option.icon && (
              <div
                className={`
                  text-2xl
                  ${isSelected ? 'text-[#E25E3E]' : 'text-gray-600'}
                `}
                aria-hidden="true"
              >
                {option.icon}
              </div>
            )}

            <div className="pr-8">
              <div
                className={`
                  text-base font-semibold
                  ${isSelected ? 'text-[#111111]' : 'text-gray-900'}
                `}
              >
                {option.label}
              </div>
              {option.description && (
                <div className="text-sm text-gray-600 mt-1">
                  {option.description}
                </div>
              )}
            </div>
          </button>
        )
      })}
    </div>
  )
}
