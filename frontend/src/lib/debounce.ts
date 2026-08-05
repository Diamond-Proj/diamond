export function debounce<TArgs extends unknown[]>(
  fn: (...args: TArgs) => void,
  delay: number
) {
  let timer: ReturnType<typeof setTimeout> | null = null;

  return (...args: TArgs): void => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}
