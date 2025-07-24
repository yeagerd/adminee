import { useState } from 'react';
import AddPackageModal from './AddPackageModal';
import PackageFilters from './PackageFilters';
import PackageList from './PackageList';

export default function PackageDashboard() {
    const [showAddModal, setShowAddModal] = useState(false);
    const [packages, setPackages] = useState<any[]>([]); // TODO: Replace any with proper type
    // TODO: Fetch packages, labels, filters, etc.

    const handleAddPackage = (pkg: any) => {
        setPackages((prev) => [pkg, ...prev]);
        setShowAddModal(false);
    };

    return (
        <div className="max-w-4xl mx-auto py-8">
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-2xl font-bold">Package Tracker</h1>
                <button
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                    onClick={() => setShowAddModal(true)}
                >
                    Add Package
                </button>
            </div>
            <PackageFilters filters={{}} onFiltersChange={() => { }} labels={[]} />
            <PackageList packages={packages} />
            {showAddModal && (
                <AddPackageModal onClose={() => setShowAddModal(false)} onAdd={handleAddPackage} />
            )}
        </div>
    );
}
