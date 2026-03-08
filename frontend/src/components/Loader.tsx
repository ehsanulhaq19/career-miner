type LoaderVariant = "default" | "auth";
type LoaderSize = "sm" | "md" | "lg";

interface LoaderProps {
  variant?: LoaderVariant;
  size?: LoaderSize;
  fullScreen?: boolean;
}

const sizeClasses: Record<LoaderSize, string> = {
  sm: "w-6 h-6 border-2",
  md: "w-8 h-8 border-4",
  lg: "w-10 h-10 border-4",
};

export default function Loader({
  variant = "default",
  size = "lg",
  fullScreen = true,
}: LoaderProps) {
  const isAuth = variant === "auth";
  const containerClass = fullScreen
    ? "min-h-screen flex items-center justify-center"
    : "flex items-center justify-center";
  const bgClass = isAuth
    ? "bg-gradient-to-br from-primary-600 via-primary-700 to-primary-900"
    : "bg-gray-50 dark:bg-gray-950";
  const spinnerClass = isAuth
    ? "border-white border-t-transparent"
    : "border-primary-600 border-t-transparent";
  const textClass = isAuth
    ? "text-sm text-primary-100"
    : "text-sm text-gray-500 dark:text-gray-400";

  const wrapperClass = fullScreen
    ? `${containerClass} ${bgClass}`
    : containerClass;

  return (
    <div className={wrapperClass}>
      <div className="flex flex-col items-center gap-4">
        <div
          className={`${sizeClasses[size]} ${spinnerClass} rounded-full animate-spin`}
        />
        <span className={textClass}>Loading...</span>
      </div>
    </div>
  );
}
