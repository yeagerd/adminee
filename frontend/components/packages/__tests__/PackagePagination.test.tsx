import { render, screen, fireEvent } from '@testing-library/react';
import PackagePagination from '../PackagePagination';

describe('PackagePagination', () => {
    const defaultProps = {
        hasNext: true,
        hasPrev: false,
        loading: false,
        onNextPage: jest.fn(),
        onPrevPage: jest.fn(),
        onFirstPage: jest.fn(),
    };

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('renders pagination controls correctly', () => {
        render(<PackagePagination {...defaultProps} />);
        
        expect(screen.getByText('First')).toBeInTheDocument();
        expect(screen.getByText('Previous')).toBeInTheDocument();
        expect(screen.getByText('Next')).toBeInTheDocument();
        expect(screen.getByText('Showing packages')).toBeInTheDocument();
    });

    it('disables Previous and First buttons when hasPrev is false', () => {
        render(<PackagePagination {...defaultProps} hasPrev={false} />);
        
        expect(screen.getByText('First')).toBeDisabled();
        expect(screen.getByText('Previous')).toBeDisabled();
        expect(screen.getByText('Next')).not.toBeDisabled();
    });

    it('disables Next button when hasNext is false', () => {
        render(<PackagePagination {...defaultProps} hasNext={false} />);
        
        expect(screen.getByText('First')).not.toBeDisabled();
        expect(screen.getByText('Previous')).not.toBeDisabled();
        expect(screen.getByText('Next')).toBeDisabled();
    });

    it('disables all buttons when loading is true', () => {
        render(<PackagePagination {...defaultProps} loading={true} />);
        
        expect(screen.getByText('First')).toBeDisabled();
        expect(screen.getByText('Previous')).toBeDisabled();
        expect(screen.getByText('Next')).toBeDisabled();
    });

    it('shows loading text when loading is true', () => {
        render(<PackagePagination {...defaultProps} loading={true} />);
        
        expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('calls onFirstPage when First button is clicked', () => {
        render(<PackagePagination {...defaultProps} hasPrev={true} />);
        
        fireEvent.click(screen.getByText('First'));
        expect(defaultProps.onFirstPage).toHaveBeenCalledTimes(1);
    });

    it('calls onPrevPage when Previous button is clicked', () => {
        render(<PackagePagination {...defaultProps} hasPrev={true} />);
        
        fireEvent.click(screen.getByText('Previous'));
        expect(defaultProps.onPrevPage).toHaveBeenCalledTimes(1);
    });

    it('calls onNextPage when Next button is clicked', () => {
        render(<PackagePagination {...defaultProps} />);
        
        fireEvent.click(screen.getByText('Next'));
        expect(defaultProps.onNextPage).toHaveBeenCalledTimes(1);
    });

    it('displays custom page info when provided', () => {
        render(
            <PackagePagination 
                {...defaultProps} 
                currentPageInfo="Showing 1-20 of 100 packages" 
            />
        );
        
        expect(screen.getByText('Showing 1-20 of 100 packages')).toBeInTheDocument();
    });

    it('handles edge case when no pagination is available', () => {
        render(
            <PackagePagination 
                {...defaultProps} 
                hasNext={false}
                hasPrev={false}
            />
        );
        
        expect(screen.getByText('First')).toBeDisabled();
        expect(screen.getByText('Previous')).toBeDisabled();
        expect(screen.getByText('Next')).toBeDisabled();
    });

    it('does not call handlers when buttons are disabled', () => {
        render(<PackagePagination {...defaultProps} hasPrev={false} hasNext={false} />);
        
        fireEvent.click(screen.getByText('First'));
        fireEvent.click(screen.getByText('Previous'));
        fireEvent.click(screen.getByText('Next'));
        
        expect(defaultProps.onFirstPage).not.toHaveBeenCalled();
        expect(defaultProps.onPrevPage).not.toHaveBeenCalled();
        expect(defaultProps.onNextPage).not.toHaveBeenCalled();
    });
}); 