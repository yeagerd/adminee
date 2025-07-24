export default function PackageList({ packages }: { packages: any[] }) {
    return (
        <div className="mt-4">
            {/* TODO: Render list of packages */}
            {packages.length === 0 ? (
                <div className="text-gray-500 text-center py-8">No packages found.</div>
            ) : (
                <ul>
                    {packages.map((pkg) => (
                        <li key={pkg.id}>{pkg.tracking_number}</li>
                    ))}
                </ul>
            )}
        </div>
    );
}
