'use client';

import { ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { MarketplaceCategoryWithChildren } from '@/lib/api';

interface CategoryFilterProps {
  categories: MarketplaceCategoryWithChildren[];
  selectedCategoryId?: string | null;
  onSelectCategory: (categoryId: string | null) => void;
}

function CategoryItem({
  category,
  selectedCategoryId,
  onSelect,
  level = 0,
}: {
  category: MarketplaceCategoryWithChildren;
  selectedCategoryId?: string | null;
  onSelect: (categoryId: string | null) => void;
  level?: number;
}) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = category.children && category.children.length > 0;
  const isSelected = selectedCategoryId === category.id;

  return (
    <div>
      <button
        onClick={() => onSelect(category.id)}
        className={`w-full flex items-center justify-between px-3 py-2 text-sm rounded-md transition-colors ${
          isSelected
            ? 'bg-primary-100 text-primary-700 font-medium'
            : 'text-gray-700 hover:bg-gray-100'
        }`}
        style={{ paddingLeft: `${level * 12 + 12}px` }}
      >
        <span className="flex items-center gap-2">
          {category.icon && (
            <span className="w-5 h-5 flex items-center justify-center text-gray-400">
              {category.icon}
            </span>
          )}
          <span>{category.name}</span>
          <span className="text-xs text-gray-400">({category.template_count})</span>
        </span>
        {hasChildren && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(!expanded);
            }}
            className="p-1 hover:bg-gray-200 rounded"
          >
            {expanded ? (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-400" />
            )}
          </button>
        )}
      </button>

      {hasChildren && expanded && (
        <div>
          {category.children.map((child) => (
            <CategoryItem
              key={child.id}
              category={child}
              selectedCategoryId={selectedCategoryId}
              onSelect={onSelect}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function CategoryFilter({
  categories,
  selectedCategoryId,
  onSelectCategory,
}: CategoryFilterProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="font-semibold text-gray-900 mb-3">Categories</h3>

      {/* All templates option */}
      <button
        onClick={() => onSelectCategory(null)}
        className={`w-full flex items-center justify-between px-3 py-2 text-sm rounded-md transition-colors mb-1 ${
          !selectedCategoryId
            ? 'bg-primary-100 text-primary-700 font-medium'
            : 'text-gray-700 hover:bg-gray-100'
        }`}
      >
        <span>All Templates</span>
      </button>

      {/* Category tree */}
      <div className="space-y-0.5">
        {categories.map((category) => (
          <CategoryItem
            key={category.id}
            category={category}
            selectedCategoryId={selectedCategoryId}
            onSelect={onSelectCategory}
          />
        ))}
      </div>
    </div>
  );
}

export default CategoryFilter;
