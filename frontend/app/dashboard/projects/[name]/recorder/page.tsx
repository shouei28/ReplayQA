export default function ProjectRecorderPage({
  params,
}: {
  params: { name: string };
}) {
  const { name } = params;
  return (
    <div>
      <h1 className="text-2xl font-bold">Recorder — {decodeURIComponent(name)}</h1>
      <p className="mt-2 text-gray-600">Record tests for this project.</p>
    </div>
  );
}
