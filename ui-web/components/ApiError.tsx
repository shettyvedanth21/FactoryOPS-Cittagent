interface ApiErrorProps {
  message: string;
}

export function ApiError({ message }: ApiErrorProps) {
  return (
    <div className="text-center p-8 bg-white dark:bg-zinc-900 rounded-lg shadow-md">
      <h2 className="text-xl font-semibold text-red-600 dark:text-red-400 mb-2">
        Unable to load data
      </h2>
      <p className="text-zinc-600 dark:text-zinc-400">{message}</p>
    </div>
  );
}
