import { SmartTimeDurationInput, parseDurationInput } from '@/components/ui/smart-time-duration-input';
import { fireEvent, render, screen } from '@testing-library/react';

describe('parseDurationInput', () => {
    test.each([
        // Pure minutes / hours heuristic
        ['45', 45],
        ['90', 90],
        ['1', 60],
        ['13', 13 * 60],
        ['14', 14 * 60],
        ['15', 15],
        ['999', 999],

        // Decimal hours (no unit) => hours
        ['1.5', 90],
        ['2.25', 135],

        // HH:MM
        ['1:30', 90],
        ['0:45', 45],

        // Suffix units
        ['45m', 45],
        ['90m', 90],
        ['1h', 60],
        ['1.5h', 90],
        ['1h30m', 90],
        ['1h 30m', 90],
        ['1hr 30min', 90],
        ['1 hr 30min', 90],
        ['1 hr 5 min', 65],
        ['1 HR 05 MIN', 65],

        // Word units (case-insensitive)
        ['1 hour', 60],
        ['2 HOURS', 120],
        ['90 minutes', 90],
        ['1.5 hours', 90],
        ['1 hour 30 minutes', 90],
        ['1 h 30 m', 90],

        // Whitespace robustness
        ['  45  m ', 45],
        [' 1 : 30 ', null], // note: spaces within HH:MM not supported
        // More creative
        ['1:15', 75],
        ['0.25h', 15],
        ['2hr', 120],
        ['75 mins', 75],
        ['90minute', 90],
        ['2 HOURS 15 MINUTES', 135],
        ['1hour 30minutes', 90],
        ['1hour30minutes', null],
        ['2h15', 135],
    ])('parses "%s" => %s minutes', (input, expected) => {
        expect(parseDurationInput(String(input))).toBe(expected as number | null);
    });

    test.each([
        ['0'],
        ['-10'],
        ['abc'],
        ['1:75'], // invalid minutes
        ['1h 75m'], // invalid minute part
        ['.5'], // leading dot not supported by parser
    ])('invalid "%s" returns null', (input) => {
        expect(parseDurationInput(input)).toBeNull();
    });
});

describe('SmartTimeDurationInput UI behavior', () => {
    function setup(initial: number = 60) {
        const onChangeMinutes = jest.fn();
        const onCancel = jest.fn();
        render(
            <SmartTimeDurationInput
                valueMinutes={initial}
                onChangeMinutes={onChangeMinutes}
                onCancel={onCancel}
            />
        );
        const input = screen.getByPlaceholderText('e.g. 45, 1.5h, 1:30') as HTMLInputElement;
        return { input, onChangeMinutes, onCancel };
    }

    test('commits parsed value on blur when valid', () => {
        const { input, onChangeMinutes } = setup(60);
        fireEvent.change(input, { target: { value: '1:30' } });
        fireEvent.blur(input);
        expect(onChangeMinutes).toHaveBeenCalledWith(90);
    });

    test('commits parsed value on Enter when valid', () => {
        const { input, onChangeMinutes } = setup(60);
        fireEvent.change(input, { target: { value: '90' } });
        fireEvent.keyDown(input, { key: 'Enter' });
        expect(onChangeMinutes).toHaveBeenCalledWith(90);
    });

    test('shows error outline when invalid on blur', () => {
        const { input, onChangeMinutes } = setup(60);
        fireEvent.change(input, { target: { value: 'abc' } });
        fireEvent.blur(input);
        expect(onChangeMinutes).not.toHaveBeenCalled();
        expect(input.className).toMatch(/border-destructive/);
    });

    test('clears error outline on focus', () => {
        const { input } = setup(60);
        fireEvent.change(input, { target: { value: 'abc' } });
        fireEvent.blur(input);
        expect(input.className).toMatch(/border-destructive/);
        fireEvent.focus(input);
        expect(input.className).not.toMatch(/border-destructive/);
    });

    test('shows grey hint for auto-detected units when no explicit unit provided', () => {
        const { input } = setup(60);
        fireEvent.change(input, { target: { value: '1.5' } });
        // Hint should say 1.5 hours
        expect(screen.getByText(/1\.5 hours/i)).toBeInTheDocument();
    });

    test('does not show hint when explicit unit provided', () => {
        const { input } = setup(60);
        fireEvent.change(input, { target: { value: '1.5h' } });
        expect(screen.queryByText(/hours?|minutes?/i)).not.toBeInTheDocument();
    });

    test('escape triggers onCancel without committing', () => {
        const { input, onCancel, onChangeMinutes } = setup(60);
        fireEvent.change(input, { target: { value: '90' } });
        fireEvent.keyDown(input, { key: 'Escape' });
        expect(onCancel).toHaveBeenCalled();
        expect(onChangeMinutes).not.toHaveBeenCalled();
    });

    test('heuristic: integer <= 14 is hours, > 14 is minutes', () => {
        const { input } = setup(60);
        fireEvent.change(input, { target: { value: '14' } });
        expect(screen.getByText(/14 hours/i)).toBeInTheDocument();
        fireEvent.change(input, { target: { value: '15' } });
        expect(screen.getByText(/15 minutes/i)).toBeInTheDocument();
    });

    test('word unit detection (starts with h/m)', () => {
        const { input, onChangeMinutes } = setup(60);
        fireEvent.change(input, { target: { value: '2 Hours' } });
        fireEvent.blur(input);
        expect(onChangeMinutes).toHaveBeenCalledWith(120);
    });
});


