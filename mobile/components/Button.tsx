import { TouchableOpacity, Text, ActivityIndicator } from 'react-native'

interface ButtonProps {
  label: string
  onPress: () => void
  disabled?: boolean
  loading?: boolean
  variant?: 'primary' | 'outline' | 'ghost'
  className?: string
}

export function Button({ label, onPress, disabled, loading, variant = 'primary', className = '' }: ButtonProps) {
  const base = 'rounded-xl py-3.5 items-center'
  const variants = {
    primary: 'bg-brand',
    outline: 'bg-white border-2 border-brand',
    ghost: 'bg-transparent',
  }
  const labelVariants = {
    primary: 'text-white font-semibold',
    outline: 'text-brand font-semibold',
    ghost: 'text-brand font-medium',
  }

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled || loading}
      className={`${base} ${variants[variant]} ${disabled || loading ? 'opacity-50' : ''} ${className}`}
    >
      {loading ? (
        <ActivityIndicator color={variant === 'primary' ? '#fff' : '#16a34a'} />
      ) : (
        <Text className={labelVariants[variant]}>{label}</Text>
      )}
    </TouchableOpacity>
  )
}
