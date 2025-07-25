export default function LabelChip({ label, color }: { label: string, color?: string }) {
    return (
        <span
            className="inline-block px-2 py-0.5 rounded text-xs font-medium mr-1"
            style={{ backgroundColor: color || '#3B82F6', color: '#fff' }}
        >
            {label}
        </span>
    );
}
