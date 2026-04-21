import { Eye, EyeOff } from 'lucide-react'
import { forwardRef, ReactElement, useState } from 'react'
import { UseFormRegisterReturn } from 'react-hook-form'
import LockIcon from '../icons/lockIcon'
import UnlockIcon from '../icons/unlockIcon'

interface PasswordInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
  error?: string
  register?: UseFormRegisterReturn
  /**
   * Whether to show the password visibility toggle button
   * @default true
   */
  showToggle?: boolean
  /**
   * Custom icon component to use as left icon (defaults to LockIcon/UnlockIcon)
   */
  setShowPassword?: (showPassword: boolean) => void
  showPassword?: boolean
  leftIcon?: ReactElement
  className?: string
}

/**
 * Password input component with visibility toggle
 * Supports react-hook-form integration
 */
const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  (
    {
      label,
      error,
      register,
      showToggle = true,
      showPassword: showPasswordProp,
      setShowPassword: setShowPasswordProp,
      leftIcon,
      className = '',
      disabled,
      id,
      ...inputProps
    },
    ref,
  ) => {
    const [internalShowPassword, setInternalShowPassword] = useState(false)
    const isControlled = setShowPasswordProp !== undefined
    const showPassword = isControlled
      ? !!showPasswordProp
      : internalShowPassword
    const setShowPassword = isControlled
      ? setShowPasswordProp!
      : setInternalShowPassword

    const lockIcon = showPassword ? (
      <UnlockIcon width={20} height={20} color="#747473" />
    ) : (
      <LockIcon width={20} height={20} color="#747473" />
    )

    // Build the input element manually to handle the toggle button properly
    const inputId = id || inputProps.name || 'password'

    const inputElement = (
      <div className="relative">
        {showToggle && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none z-10">
            {lockIcon}
          </div>
        )}
        {!showToggle && leftIcon && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            {leftIcon}
          </div>
        )}

        <input
          ref={ref}
          id={inputId}
          type={showPassword ? 'text' : 'password'}
          className={`pl-10 pr-10 w-full px-3 py-2 border border-input rounded-md focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-colors ${disabled ? 'disabled:bg-gray-100' : ''} ${className}`}
          placeholder={inputProps.placeholder || '********'}
          disabled={disabled}
          {...inputProps}
          {...register}
        />

        {showToggle && (
          <button
            type="button"
            tabIndex={-1}
            onClick={() => setShowPassword(!showPassword)}
            aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-500 hover:text-gray-700 z-10"
            disabled={disabled}
          >
            {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
          </button>
        )}
      </div>
    )

    if (label) {
      return (
        <div className="flex flex-col">
          <label htmlFor={inputId} className="mb-1 font-medium">
            {label}
          </label>
          {inputElement}
          {error && <div className="text-red-500 text-sm mt-1">{error}</div>}
        </div>
      )
    }

    return inputElement
  },
)

PasswordInput.displayName = 'PasswordInput'

export default PasswordInput
