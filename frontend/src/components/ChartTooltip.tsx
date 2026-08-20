export function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-xl px-3 py-2 text-sm shadow-2xl">
      <p className="text-muted-foreground text-xs mb-0.5">{label}</p>
      <p className="text-foreground font-semibold">{payload[0].value}h de sono</p>
    </div>
  );
}
