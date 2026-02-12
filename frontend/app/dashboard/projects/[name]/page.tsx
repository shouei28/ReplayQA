export default function ProjectDetailPage({
  params,
}: {
  params: { name: string };
}) {
  const { name } = params;
  return (
    <div>
      <h1 className="text-2xl font-bold">Project: {decodeURIComponent(name)}</h1>
      <p className="mt-2 text-gray-600">Project tests, execution, settings.</p>
    </div>
  );
}
