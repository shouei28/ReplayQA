export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="min-h-screen">
      <aside className="border-r p-4 w-48">Dashboard nav</aside>
      <div className="p-8">{children}</div>
    </div>
  );
}
