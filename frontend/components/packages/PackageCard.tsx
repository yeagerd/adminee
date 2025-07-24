export default function PackageCard({ pkg }: { pkg: any }) {
    return (
        <div className="border rounded p-4 mb-2">
            <div className="font-bold">{pkg.tracking_number}</div>
            <div className="text-sm text-gray-500">{pkg.carrier}</div>
        </div>
    );
}
