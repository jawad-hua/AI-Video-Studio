import { cn } from "@/lib/utils";

interface Option<T> {
  value: T;
  label: string;
}

interface Props<T extends string | number> {
  options: Option<T>[];
  value: T;
  onChange: (value: T) => void;
  disabled?: boolean;
  label: string;
}

export default function Segmented<T extends string | number>({
  options,
  value,
  onChange,
  disabled,
  label,
}: Props<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="inline-flex rounded-xl border border-white/10 bg-black/30 p-1"
    >
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={String(o.value)}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={disabled}
            onClick={() => onChange(o.value)}
            className={cn(
              "rounded-lg px-3.5 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed",
              active ? "accent-bg text-white shadow" : "text-white/60 hover:text-white",
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
