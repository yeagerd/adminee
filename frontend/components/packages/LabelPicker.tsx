export default function LabelPicker({ labels, selectedLabels, onChange }: {
    labels: { id: string, name: string, color: string }[],
    selectedLabels: string[],
    onChange: (labels: string[]) => void,
}) {
    return (
        <div className="flex flex-wrap gap-2">
            {labels.map(label => (
                <label key={label.id} className="flex items-center gap-1 cursor-pointer">
                    <input
                        type="checkbox"
                        checked={selectedLabels.includes(label.name)}
                        onChange={e => {
                            if (e.target.checked) {
                                onChange([...selectedLabels, label.name]);
                            } else {
                                onChange(selectedLabels.filter(l => l !== label.name));
                            }
                        }}
                    />
                    <span style={{ backgroundColor: label.color, color: '#fff', borderRadius: 4, padding: '0 6px' }}>{label.name}</span>
                </label>
            ))}
        </div>
    );
}
