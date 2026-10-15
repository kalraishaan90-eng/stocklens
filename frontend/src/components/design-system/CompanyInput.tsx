import React, { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Search, X, Check, Building2 } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface CompanyOption {
  symbol: string;
  name: string;
  exchange?: string;
  sector?: string;
}

export interface CompanyInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  onSelectOption?: (option: CompanyOption) => void;
  accent?: 'gold' | 'cyan' | 'pepper' | 'blood' | 'default';
  accentNumber?: 1 | 2;
  placeholder?: string;
  suggestions?: CompanyOption[];
  disabled?: boolean;
  className?: string;
}

const DEFAULT_INDIAN_STOCKS: CompanyOption[] = [
  { symbol: 'HAL', name: 'Hindustan Aeronautics Ltd', exchange: 'NSE', sector: 'Defense' },
  { symbol: 'MAZDOCK', name: 'Mazagon Dock Shipbuilders Ltd', exchange: 'NSE', sector: 'Defense' },
  { symbol: 'RELIANCE', name: 'Reliance Industries Ltd', exchange: 'NSE', sector: 'Energy & Conglomerate' },
  { symbol: 'TCS', name: 'Tata Consultancy Services Ltd', exchange: 'NSE', sector: 'Technology' },
  { symbol: 'HDFCBANK', name: 'HDFC Bank Ltd', exchange: 'NSE', sector: 'Financials' },
  { symbol: 'INFY', name: 'Infosys Ltd', exchange: 'NSE', sector: 'Technology' },
  { symbol: 'ICICIBANK', name: 'ICICI Bank Ltd', exchange: 'NSE', sector: 'Financials' },
  { symbol: 'BHARTIARTL', name: 'Bharti Airtel Ltd', exchange: 'NSE', sector: 'Telecom' },
  { symbol: 'SBIN', name: 'State Bank of India', exchange: 'NSE', sector: 'Public Banking' },
  { symbol: 'ITC', name: 'ITC Ltd', exchange: 'NSE', sector: 'FMCG' },
  { symbol: 'LT', name: 'Larsen & Toubro Ltd', exchange: 'NSE', sector: 'Capital Goods' },
  { symbol: 'BEL', name: 'Bharat Electronics Ltd', exchange: 'NSE', sector: 'Defense' },
  { symbol: 'TATASTEEL', name: 'Tata Steel Ltd', exchange: 'NSE', sector: 'Metals' },
];

export const CompanyInput: React.FC<CompanyInputProps> = ({
  label,
  value,
  onChange,
  onSelectOption,
  accent = 'gold',
  accentNumber,
  placeholder = 'Search ticker or company name...',
  suggestions = DEFAULT_INDIAN_STOCKS,
  disabled = false,
  className,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState(value);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Sync internal state with external value
  useEffect(() => {
    setQuery(value);
  }, [value]);

  // Filter suggestions
  const filtered = suggestions.filter((item) => {
    const q = query.toLowerCase().trim();
    if (!q) return true;
    return (
      item.symbol.toLowerCase().includes(q) ||
      item.name.toLowerCase().includes(q) ||
      (item.sector && item.sector.toLowerCase().includes(q))
    );
  }).slice(0, 6);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (option: CompanyOption) => {
    setQuery(option.symbol);
    onChange(option.symbol);
    if (onSelectOption) onSelectOption(option);
    setIsOpen(false);
  };

  const handleClear = () => {
    setQuery('');
    onChange('');
    setIsOpen(false);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen && (e.key === 'ArrowDown' || e.key === 'Enter')) {
      setIsOpen(true);
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev + 1) % Math.max(1, filtered.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev - 1 + filtered.length) % Math.max(1, filtered.length));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filtered[highlightedIndex]) {
        handleSelect(filtered[highlightedIndex]);
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  const accentStyles = {
    pepper: {
      badge: 'bg-pepper/15 text-pepper border-pepper/35',
      glow: 'focus-within:border-pepper/60 focus-within:ring-pepper/30',
      activeItem: 'bg-pepper/10 text-editorial-primary',
      dot: 'bg-pepper',
    },
    blood: {
      badge: 'bg-blood/20 text-pepper-light border-blood-border',
      glow: 'focus-within:border-blood/60 focus-within:ring-blood/30',
      activeItem: 'bg-blood/15 text-editorial-primary',
      dot: 'bg-blood',
    },
    gold: {
      badge: 'bg-gold/15 text-gold border-gold/30',
      glow: 'focus-within:border-gold/60 focus-within:ring-gold/30',
      activeItem: 'bg-gold/10 text-editorial-primary',
      dot: 'bg-gold',
    },
    cyan: {
      badge: 'bg-cyan/15 text-cyan border-cyan/30',
      glow: 'focus-within:border-cyan/60 focus-within:ring-cyan/30',
      activeItem: 'bg-cyan/10 text-editorial-primary',
      dot: 'bg-cyan',
    },
    default: {
      badge: 'bg-surface-raised text-editorial-primary border-editorial-subtle',
      glow: 'focus-within:border-editorial-strong focus-within:ring-editorial-primary/20',
      activeItem: 'bg-surface-raised text-editorial-primary',
      dot: 'bg-editorial-primary',
    },
  }[accent || 'gold'];

  // Check if current value matches an exact company
  const matchedCompany = suggestions.find(
    (s) => s.symbol.toUpperCase() === value.trim().toUpperCase()
  );

  return (
    <div ref={containerRef} className={twMerge(clsx('relative w-full text-left font-sans', className))}>
      {/* Label and Eyebrow */}
      <div className="flex items-center justify-between mb-1.5 px-0.5">
        <label className="text-xs uppercase tracking-wider font-semibold text-editorial-secondary flex items-center gap-1.5">
          {accentNumber && (
            <span
              className={clsx(
                'w-4 h-4 rounded-full text-[10px] font-mono font-bold flex items-center justify-center border',
                accent === 'pepper' ? 'border-pepper/40 text-pepper bg-pepper/10' :
                accent === 'blood' ? 'border-blood/40 text-pepper bg-blood/20' :
                accent === 'gold' ? 'border-gold/40 text-gold bg-gold/10' : 'border-cyan/40 text-cyan bg-cyan/10'
              )}
            >
              {accentNumber}
            </span>
          )}
          <span>{label}</span>
        </label>
        {matchedCompany && (
          <span className="text-[11px] font-mono text-editorial-muted truncate max-w-[200px]">
            {matchedCompany.name}
          </span>
        )}
      </div>

      {/* Input Container */}
      <div
        className={clsx(
          'relative flex items-center rounded-lg bg-surface-card border border-editorial-hairline transition-all duration-200 shadow-hairline',
          'hover:border-editorial-subtle focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-offset-base',
          accentStyles.glow,
          disabled && 'opacity-50 pointer-events-none'
        )}
      >
        {/* Leading Search Icon / Dot */}
        <div className="pl-3.5 pr-2 flex items-center pointer-events-none text-editorial-muted">
          <Search className="w-4 h-4" />
        </div>

        {/* Input */}
        <input
          ref={inputRef}
          type="text"
          value={query}
          disabled={disabled}
          onChange={(e) => {
            setQuery(e.target.value);
            onChange(e.target.value);
            setIsOpen(true);
            setHighlightedIndex(0);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full py-2.5 bg-transparent text-editorial-primary placeholder:text-editorial-muted text-sm font-sans focus:outline-none"
        />

        {/* Selected Ticker Chip & Clear Button */}
        <div className="pr-2 flex items-center gap-1.5">
          {value && (
            <div
              className={clsx(
                'px-2 py-0.5 rounded text-xs font-mono font-medium border flex items-center gap-1 tracking-wider',
                accentStyles.badge
              )}
            >
              <span className={clsx('w-1.5 h-1.5 rounded-full', accentStyles.dot)} />
              <span>{value.toUpperCase()}</span>
            </div>
          )}

          {query && (
            <button
              type="button"
              onClick={handleClear}
              className="p-1 rounded-md text-editorial-muted hover:text-editorial-primary hover:bg-surface-raised transition-colors cursor-pointer"
              title="Clear input"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Autocomplete Dropdown */}
      {isOpen && (
        <div className="absolute z-50 mt-1.5 w-full rounded-card bg-surface-card border border-editorial-hairline shadow-2xl py-1.5 overflow-hidden backdrop-blur-xl animate-fadeIn">
          <div className="px-3 py-1 text-[11px] font-mono uppercase tracking-wider text-editorial-muted border-b border-editorial-hairline/60 flex items-center justify-between">
            <span>Verified Market Equities</span>
            <span>NSE / BSE</span>
          </div>

          {filtered.length === 0 ? (
            <div className="px-4 py-3 text-xs text-editorial-muted text-center font-mono">
              No ticker matching "{query}". Enter exact symbol to analyze.
            </div>
          ) : (
            <ul className="max-h-60 overflow-y-auto divide-y divide-editorial-hairline/30">
              {filtered.map((item, idx) => {
                const isSelected = item.symbol.toUpperCase() === value.toUpperCase();
                const isHighlighted = idx === highlightedIndex;

                return (
                  <li
                    key={item.symbol}
                    onMouseEnter={() => setHighlightedIndex(idx)}
                    onClick={() => handleSelect(item)}
                    className={clsx(
                      'px-3.5 py-2.5 flex items-center justify-between cursor-pointer transition-colors text-xs',
                      isHighlighted ? accentStyles.activeItem : 'hover:bg-surface-raised',
                      isSelected && 'font-semibold text-editorial-primary'
                    )}
                  >
                    <div className="flex items-center gap-2.5 truncate">
                      <div className="w-7 h-7 rounded bg-surface-raised border border-editorial-hairline flex items-center justify-center shrink-0">
                        <Building2 className="w-3.5 h-3.5 text-editorial-secondary" />
                      </div>
                      <div className="truncate">
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono font-bold text-editorial-primary tracking-wide">
                            {item.symbol}
                          </span>
                          {item.exchange && (
                            <span className="text-[10px] px-1 py-0.2 rounded bg-surface-raised text-editorial-muted font-mono">
                              {item.exchange}
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-editorial-secondary truncate max-w-[220px]">
                          {item.name}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {item.sector && (
                        <span className="text-[10px] text-editorial-muted hidden sm:inline-block font-sans">
                          {item.sector}
                        </span>
                      )}
                      {isSelected && <Check className="w-3.5 h-3.5 text-gold shrink-0" />}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};
