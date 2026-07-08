export function SkeletonCard() {
  return (
    <div className="glass-card p-5 animate-pulse">
      <div className="h-4 w-2/5 bg-border rounded-sm mb-6" />
      <div className="flex justify-center mb-4">
        <div className="w-[88px] h-[88px] rounded-full bg-border" />
      </div>
      <div className="h-3 w-1/3 bg-border rounded-sm mx-auto mb-3" />
      <div className="h-6 w-24 bg-border rounded-md mx-auto" />
    </div>
  )
}
