export default function Panel({ title, children, className = "" }: { title?: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`panel p-4 ${className}`}>
      {title && <h3 className="text-sm font-semibold mb-3 text-text-primary">{title}</h3>}
      {children}
    </section>
  );
}
