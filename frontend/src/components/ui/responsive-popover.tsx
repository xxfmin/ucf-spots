"use client";

import { useSyncExternalStore, type ReactNode } from "react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Dialog,
  DialogContent,
  DialogTrigger,
  DialogTitle,
} from "@/components/ui/dialog";

const MOBILE_DIALOG_CLASS =
  "bg-surface-raised border-border-muted text-zinc-200 [&>button]:top-3 [&>button]:right-3 !duration-200 data-[state=open]:!slide-in-from-top-0 data-[state=closed]:!slide-out-to-top-0 data-[state=open]:!slide-in-from-left-0 data-[state=closed]:!slide-out-to-left-0 data-[state=open]:!zoom-in-100 data-[state=closed]:!zoom-out-100";

const DESKTOP_MQ = "(min-width: 768px)";

function subscribeDesktop(callback: () => void): () => void {
  const mq = window.matchMedia(DESKTOP_MQ);
  mq.addEventListener("change", callback);
  return () => mq.removeEventListener("change", callback);
}

/**
 * Shared hook — matches `(min-width: 768px)`. Returns `false` during SSR and
 * on the first client paint, then syncs without triggering a cascading render.
 */
export function useIsDesktop(): boolean {
  return useSyncExternalStore(
    subscribeDesktop,
    () => window.matchMedia(DESKTOP_MQ).matches,
    () => false,
  );
}

/**
 * `true` once the component has mounted on the client. Uses
 * `useSyncExternalStore` so SSR snapshot differs from client snapshot
 * without an effect-driven state update.
 */
export function useMounted(): boolean {
  return useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
}

interface ResponsivePopoverProps {
  trigger: ReactNode;
  children: ReactNode;
  title: string;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  desktopContentClassName?: string;
  mobileContentClassName?: string;
  desktopAlign?: "start" | "center" | "end";
  desktopSideOffset?: number;
  desktopCollisionPadding?: number;
}

/**
 * Renders a Popover on desktop and a Dialog on mobile with a single API.
 * Avoids SSR hydration mismatch by waiting for mount before branching.
 */
export function ResponsivePopover({
  trigger,
  children,
  title,
  open,
  onOpenChange,
  desktopContentClassName,
  mobileContentClassName,
  desktopAlign,
  desktopSideOffset,
  desktopCollisionPadding,
}: ResponsivePopoverProps) {
  const mounted = useMounted();
  const isDesktop = useIsDesktop();

  // Before mount, render only the trigger inside a neutral wrapper so the
  // server HTML and first client paint match.
  if (!mounted) {
    return <>{trigger}</>;
  }

  if (isDesktop) {
    return (
      <Popover open={open} onOpenChange={onOpenChange}>
        <PopoverTrigger asChild>{trigger}</PopoverTrigger>
        <PopoverContent
          align={desktopAlign}
          sideOffset={desktopSideOffset}
          collisionPadding={desktopCollisionPadding}
          className={desktopContentClassName}
        >
          {children}
        </PopoverContent>
      </Popover>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent
        className={
          mobileContentClassName ??
          `w-[min(20rem,calc(100vw-2rem))] max-w-[calc(100vw-2rem)] ${MOBILE_DIALOG_CLASS}`
        }
      >
        <DialogTitle className="sr-only">{title}</DialogTitle>
        {children}
      </DialogContent>
    </Dialog>
  );
}
