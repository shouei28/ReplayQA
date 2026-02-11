/**
 * Merge class names. Add clsx for full support when using Shadcn.
 */
export function cn(...inputs: (string | undefined | null | false)[]) {
  return inputs.filter(Boolean).join(" ");
}
