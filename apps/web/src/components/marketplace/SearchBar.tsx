'use client';

import { Search, X, SlidersHorizontal } from 'lucide-react';
import { useState } from 'react';

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  onAdvancedFilters?: () => void;
  showAdvancedFilters?: boolean;
}

export function SearchBar({
  value,
  onChange,
  placeholder = 'Search templates...',
  onAdvancedFilters,
  showAdvancedFilters = false,
}: SearchBarProps) {
  const [focused, setFocused] = useState(false);

  return (
    <div
      className={`flex items-center gap-2 bg-white border rounded-lg px-4 py-2 transition-all ${
        focused
          ? 'border-primary-500 ring-2 ring-primary-100'
          : 'border-gray-200'
      }`}
    >
      <Search className="w-5 h-5 text-gray-400 flex-shrink-0" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={placeholder}
        className="flex-1 outline-none text-gray-900 placeholder-gray-400"
      />
      {value && (
        <button
          onClick={() => onChange('')}
          className="p-1 hover:bg-gray-100 rounded-full transition-colors"
        >
          <X className="w-4 h-4 text-gray-400" />
        </button>
      )}
      {showAdvancedFilters && onAdvancedFilters && (
        <button
          onClick={onAdvancedFilters}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors flex items-center gap-1 text-sm text-gray-600"
        >
          <SlidersHorizontal className="w-4 h-4" />
          <span className="hidden sm:inline">Filters</span>
        </button>
      )}
    </div>
  );
}

interface FilterBarProps {
  sortBy: string;
  onSortChange: (value: string) => void;
  filters: {
    is_featured?: boolean;
    is_verified?: boolean;
    is_premium?: boolean;
    min_rating?: number;
  };
  onFilterChange: (key: string, value: unknown) => void;
}

export function FilterBar({
  sortBy,
  onSortChange,
  filters,
  onFilterChange,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Sort dropdown */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-500">Sort by:</span>
        <select
          value={sortBy}
          onChange={(e) => onSortChange(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-500"
        >
          <option value="popular">Most Popular</option>
          <option value="newest">Newest</option>
          <option value="rating">Top Rated</option>
          <option value="usage">Most Used</option>
          <option value="name">Name (A-Z)</option>
        </select>
      </div>

      {/* Quick filters */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => onFilterChange('is_featured', !filters.is_featured)}
          className={`text-sm px-3 py-1.5 rounded-lg border transition-colors ${
            filters.is_featured
              ? 'bg-yellow-50 border-yellow-300 text-yellow-700'
              : 'border-gray-200 text-gray-600 hover:bg-gray-50'
          }`}
        >
          Featured
        </button>
        <button
          onClick={() => onFilterChange('is_verified', !filters.is_verified)}
          className={`text-sm px-3 py-1.5 rounded-lg border transition-colors ${
            filters.is_verified
              ? 'bg-green-50 border-green-300 text-green-700'
              : 'border-gray-200 text-gray-600 hover:bg-gray-50'
          }`}
        >
          Verified
        </button>
        <button
          onClick={() =>
            onFilterChange('is_premium', filters.is_premium === true ? undefined : false)
          }
          className={`text-sm px-3 py-1.5 rounded-lg border transition-colors ${
            filters.is_premium === false
              ? 'bg-primary-50 border-primary-300 text-primary-700'
              : 'border-gray-200 text-gray-600 hover:bg-gray-50'
          }`}
        >
          Free Only
        </button>
      </div>

      {/* Rating filter */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-500">Min rating:</span>
        <select
          value={filters.min_rating || ''}
          onChange={(e) =>
            onFilterChange('min_rating', e.target.value ? Number(e.target.value) : undefined)
          }
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-500"
        >
          <option value="">Any</option>
          <option value="4">4+ stars</option>
          <option value="3">3+ stars</option>
          <option value="2">2+ stars</option>
        </select>
      </div>
    </div>
  );
}

export default SearchBar;
