import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap text-sm font-mono ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/50 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        // Primary: White background, black text (main CTA)
        default: 'bg-white text-black hover:bg-white/90',
        primary: 'bg-white text-black hover:bg-white/90',

        // Secondary: Outline style with white border
        secondary: 'border border-white/20 bg-transparent text-white/60 hover:bg-white/5 hover:text-white',

        // Outline: Same as secondary (alias)
        outline: 'border border-white/20 bg-transparent text-white/60 hover:bg-white/5 hover:text-white',

        // Ghost: No border, subtle hover
        ghost: 'bg-transparent text-white/60 hover:bg-white/5 hover:text-white',

        // Destructive: Red theme for delete actions
        destructive: 'border border-red-500/30 bg-transparent text-red-400 hover:bg-red-500/10',

        // Success: Green theme
        success: 'border border-green-500/30 bg-transparent text-green-400 hover:bg-green-500/10',

        // Warning: Yellow theme
        warning: 'border border-yellow-500/30 bg-transparent text-yellow-400 hover:bg-yellow-500/10',

        // Link: Text only with underline
        link: 'text-white/60 underline-offset-4 hover:underline hover:text-white',

        // Menu item: For dropdown menus
        menu: 'w-full justify-start bg-transparent text-white/60 hover:bg-white/10 hover:text-white',
      },
      size: {
        default: 'h-9 px-4 py-2 text-xs',
        sm: 'h-7 px-3 text-[10px]',
        lg: 'h-11 px-6 text-sm',
        icon: 'h-9 w-9',
        'icon-sm': 'h-7 w-7',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
