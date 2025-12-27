interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export default function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  const pages = Array.from({ length: totalPages }, (_, i) => i + 1);
  
  const visiblePages = pages.filter(page => {
    if (totalPages <= 7) return true;
    if (page === 1 || page === totalPages) return true;
    if (page >= currentPage - 1 && page <= currentPage + 1) return true;
    return false;
  });

  return (
    <div className="flex items-center justify-center gap-2">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className="px-3 py-2 rounded border disabled:opacity-50 hover:bg-gray-50"
      >
        Previous
      </button>

      {visiblePages.map((page, idx) => {
        if (idx > 0 && visiblePages[idx - 1] !== page - 1) {
          return (
            <span key={`ellipsis-${page}`}>
              <span className="px-2">...</span>
              <button
                onClick={() => onPageChange(page)}
                className={`px-3 py-2 rounded border ${
                  currentPage === page ? 'bg-blue-600 text-white' : 'hover:bg-gray-50'
                }`}
              >
                {page}
              </button>
            </span>
          );
        }
        
        return (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            className={`px-3 py-2 rounded border ${
              currentPage === page ? 'bg-blue-600 text-white' : 'hover:bg-gray-50'
            }`}
          >
            {page}
          </button>
        );
      })}

      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className="px-3 py-2 rounded border disabled:opacity-50 hover:bg-gray-50"
      >
        Next
      </button>
    </div>
  );
}

