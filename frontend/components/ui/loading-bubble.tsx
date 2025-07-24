import React from 'react';
import './loading-animation.css';

const LoadingBubble = () => {
    return (
        <div className="loading-bubble">
            <div className="loading-dot"></div>
            <div className="loading-dot"></div>
            <div className="loading-dot"></div>
        </div>
    );
};

export default LoadingBubble;
