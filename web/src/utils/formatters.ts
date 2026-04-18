/**
 * Convert ALL-CAPS franchise name to Title Case.
 * "CACAU SHOW" → "Cacau Show", "O BOTICÁRIO" → "O Boticário"
 * Preserves already mixed-case names like "McDonald's".
 */
export function formatFranchiseName(name: string): string {
  if (!name) return name
  // Only transform if mostly uppercase (>70% caps)
  const letters = name.replace(/[^a-zA-ZÀ-ÿ]/g, '')
  const upperCount = (letters.match(/[A-ZÀ-Ý]/g) || []).length
  if (letters.length === 0 || upperCount / letters.length < 0.7) return name

  return name
    .toLowerCase()
    .replace(
      /(^|\s|[-/(])(\S)/g,
      (_, prefix, char) => prefix + char.toUpperCase(),
    )
}

/**
 * Format a single currency value
 */
export const formatCurrency = (value: number | null | undefined): string => {
  if (
    value === null ||
    value === undefined ||
    isNaN(Number(value)) ||
    Number(value) === 0
  ) {
    return 'Consulte'
  }
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Number(value))
}

/**
 * Format a currency value in compact format (k for thousands, M for millions)
 * Examples:
 * - 300.000 → "R$ 300k"
 * - 1.000.000 → "R$ 1.0M"
 * - 1.500.000 → "R$ 1.5M"
 * - 50.000 → "R$ 50k"
 */
const formatCurrencyCompact = (value: number): string => {
  const numValue = Number(value)

  if (numValue >= 1000000) {
    // Format as millions with one decimal place if needed
    const millions = numValue / 1000000
    // Check if the result is very close to a whole number (within small epsilon)
    const formatted =
      Math.abs(millions - Math.round(millions)) < 0.001
        ? Math.round(millions).toFixed(0)
        : millions.toFixed(1)
    return `R$ ${formatted}M`
  }

  if (numValue >= 1000) {
    // Format as thousands with one decimal place if needed
    const thousands = numValue / 1000
    // Check if the result is very close to a whole number (within small epsilon)
    const formatted =
      Math.abs(thousands - Math.round(thousands)) < 0.001
        ? Math.round(thousands).toFixed(0)
        : thousands.toFixed(1)
    return `R$ ${formatted}k`
  }

  // For values less than 1000, use standard formatting
  return formatCurrency(value)
}

/**
 * Format an investment range (minimum and maximum)
 * Examples:
 * - Both values: "R$ 50k - R$ 100k" or "R$ 1.0M - R$ 1.5M"
 * - Only minimum: "R$ 50k" or "R$ 1.0M"
 * - No values, zero values, or minimum is 0/null: "Consulte"
 */
export const formatInvestmentRange = (
  min: number | null | undefined,
  max: number | null | undefined,
): string => {
  // Check if minimum is null, undefined, or zero - show "Consulte"
  const minValue = min === null || min === undefined ? 0 : Number(min)

  if (minValue === 0 || !min) {
    return 'Consulte'
  }

  // If both values exist and are valid, show range
  if (max && Number(max) > 0 && Number(max) !== minValue) {
    return `${formatCurrencyCompact(min)} - ${formatCurrencyCompact(max)}`
  }

  // Single value
  return formatCurrencyCompact(min)
}

/**
 * Format ROI range in months
 * Examples:
 * - Both values: "12-18 meses"
 * - Only minimum: "12 meses"
 * - No values or zero values: "Consulte"
 */
export const formatROIRange = (
  min: number | null | undefined,
  max: number | null | undefined,
): string => {
  // Check if both values are null, undefined, or zero
  const minValue = min === null || min === undefined ? 0 : Number(min)
  const maxValue = max === null || max === undefined ? 0 : Number(max)

  if ((!minValue && !maxValue) || (minValue === 0 && maxValue === 0)) {
    return 'Consulte'
  }
  if (!max || min === max) {
    // If single value is 0 or invalid, return "Consulte"
    if (minValue === 0) return 'Consulte'
    return `${min} meses`
  }
  // If either value in range is 0, show "Consulte"
  if (minValue === 0 || maxValue === 0) return 'Consulte'
  return `${min}-${max} meses`
}

/**
 * Format a percentage value
 */
export const formatPercentage = (value: number | null | undefined): string => {
  if (value === null || value === undefined || isNaN(Number(value))) {
    return 'N/A'
  }
  return `${value.toFixed(1)}%`
}

/**
 * Format a macro-data date string straight from the pipeline.
 *
 * Inputs:
 *   "YYYY-MM-DD" (BCB/IBGE daily/quarterly) → "DD/MM/YYYY"
 *   "YYYY-MM"    (IBGE/PMC monthly)         → "MM/YYYY"
 *   null / undefined / empty                → "—"
 *
 * Does NOT parse through Date() — a bare "YYYY-MM-DD" parsed as Date gets
 * shifted by UTC offset and silently becomes the day before in America/Sao_Paulo.
 */
export function formatDataMacro(raw: string | null | undefined): string {
  if (!raw) return '—'
  const datePart = raw.split('T')[0]
  const parts = datePart.split('-')
  if (parts.length === 3) {
    const [year, month, day] = parts
    return `${day}/${month}/${year}`
  }
  if (parts.length === 2) {
    const [year, month] = parts
    return `${month}/${year}`
  }
  return raw
}
