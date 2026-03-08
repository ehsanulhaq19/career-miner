export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-600 via-primary-700 to-primary-900">
      <div className="w-full max-w-md px-4">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white tracking-tight">
            CareerMiner
          </h1>
          <p className="mt-2 text-primary-200">
            Discover opportunities, automated
          </p>
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl p-8">
          {children}
        </div>
      </div>
    </div>
  );
}
