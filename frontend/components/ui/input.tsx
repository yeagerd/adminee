"use client";

import * as React from 'react';

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(function Input({ className = '', ...props }, ref) {
    return (
        <input ref={ref} className={`border rounded px-2 py-1 ${className}`} {...props} />
    );
});

export default Input;
