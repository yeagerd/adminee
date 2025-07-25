import * as React from "react";

function isMobileUserAgent() {
    if (typeof navigator === "undefined") return false;
    return /Mobi|Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

export function useIsMobile() {
    const [isMobile, setIsMobile] = React.useState<boolean>(false)

    React.useEffect(() => {
        setIsMobile(isMobileUserAgent())
    }, [])

    return isMobile
}
