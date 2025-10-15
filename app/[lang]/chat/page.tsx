"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "@/components/ui/resizable";
import {
  PanelRight,
  MessageSquare,
  ChevronLeft,
  ChevronRight,
  Home,
  FileText,
  Sparkles,
  Settings,
  HelpCircle,
  Edit3,
  Copy,
  Share2,
  Trash2,
  Search,
  MoreHorizontal,
  Plus,
  FolderPlus,
  FolderClosed,
  Pin,
} from "lucide-react";
import type { ImperativePanelHandle } from "react-resizable-panels";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";

export default function ChatLayoutResizable() {
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const [isLeftCollapsed, setIsLeftCollapsed] = React.useState(false);
  const [isRightCollapsed, setIsRightCollapsed] = React.useState(true);

  const leftRef = React.useRef<ImperativePanelHandle>(null);
  const rightRef = React.useRef<ImperativePanelHandle>(null);

  // ----- State: threads & selection (shared for pinned + list) -----
  const [threads, setThreads] = React.useState<Thread[]>(INITIAL_THREADS);
  const [selectedId, setSelectedId] = React.useState<string | null>(
    INITIAL_THREADS[0]?.id ?? null
  );

  // layout defaults (useState generic on the function, NOT on the LHS tuple)
  const [defaults, setDefaults] = React.useState<{
    threads: number;
    chat: number;
    prompts: number;
  }>({
    threads: 18,
    chat: 64,
    prompts: 18,
  });

  React.useEffect(() => {
    const w = window.innerWidth;
    if (w <= 1366) {
      setDefaults({ threads: 20, chat: 60, prompts: 20 });
    } else {
      setDefaults({ threads: 18, chat: 64, prompts: 18 });
    }
  }, []);

  // Prompt area: start collapsed by default
  React.useEffect(() => {
    rightRef.current?.collapse();
    setIsRightCollapsed(true);
  }, []);

  // Auto scroll messages to bottom on first render
  React.useEffect(() => {
    const viewport = document.querySelector(
      "#chat-scroll-area [data-radix-scroll-area-viewport]"
    ) as HTMLElement | null;
    if (viewport) {
      requestAnimationFrame(() => {
        viewport.scrollTop = viewport.scrollHeight;
      });
    }
  }, []);

  const leftPanels = [
    <ResizablePanel
      ref={leftRef}
      key="threads"
      order={1}
      defaultSize={defaults.threads}
      minSize={10}
      maxSize={26}
      collapsible
      collapsedSize={0}
      className="relative z-40 min-w-0 border-r border-border bg-background overflow-visible"
      style={{ overflow: isLeftCollapsed ? "hidden" : "visible" }}
    >
      {!isLeftCollapsed && (
        <div className="absolute top-1 right-0 translate-x-[calc(100%+8px)] z-[90]">
          <ActionIcon
            tooltip="閉じる"
            onClick={() => {
              leftRef.current?.collapse();
              setIsLeftCollapsed(true);
            }}
          >
            <ChevronLeft className="h-4 w-4" />
          </ActionIcon>
        </div>
      )}
      <div className="p-2 space-y-2">
        {/* Top actions */}
        <div className="grid grid-cols-[1fr_auto] items-center gap-2 w-full">
          <Button
            size="sm"
            variant="ghost"
            className="h-8 flex-1 min-w-0 px-2 overflow-hidden justify-start gap-2 rounded-xl border border-border bg-card/50 hover:bg-accent/50 text-foreground shadow-sm"
            title="新しいチャット"
          >
            <Plus className="h-4 w-4 shrink-0" />
            <span className="truncate">新しいチャット</span>
          </Button>
          <Button
            size="icon"
            variant="ghost"
            className="h-8 w-8 shrink-0 rounded-xl border border-border bg-card/50 hover:bg-accent/50 text-foreground shadow-sm"
            title="フォルダ作成"
          >
            <FolderPlus className="h-4 w-4" />
          </Button>
        </div>
        <div className="mb-2 flex items-center gap-2 rounded-xl bg-primary px-2 py-1.5 text-primary-foreground">
          <Search className="h-4 w-4 text-primary-foreground/80" />
          <Input
            className="h-7 border-0 bg-transparent p-0 text-sm focus-visible:ring-0 text-primary-foreground placeholder:text-primary-foreground/70"
            placeholder="スレッドを検索..."
          />
        </div>
      </div>
      <ScrollArea className="h-[calc(100%-44px-48px)] px-2 pb-2">
        {/* Pinned section */}
        <div className="mb-2">
          <div className="sticky top-0 z-10 bg-background/95 px-2 py-1 text-xs font-semibold text-muted-foreground">
            ピン留め
          </div>
          <PinnedList
            threads={threads}
            selectedId={selectedId}
            onSelect={(id) => setSelectedId(id)}
            onPinToggle={(id) =>
              setThreads((prev) =>
                prev.map((t) => (t.id === id ? { ...t, pinned: !t.pinned } : t))
              )
            }
          />
        </div>

        {/* Folders placeholder */}
        <div className="mb-2">
          <div className="sticky top-0 z-10 bg-background/95 px-2 py-1 text-xs font-semibold text-muted-foreground">
            フォルダ
          </div>
          <FolderList />
        </div>

        <div className="sticky top-0 z-10 bg-background/95 px-2 py-1 text-xs font-semibold text-muted-foreground">
          最近のスレッド
        </div>
        <ThreadList
          threads={threads}
          selectedId={selectedId}
          onSelect={(id) => setSelectedId(id)}
          onPinToggle={(id) =>
            setThreads((prev) =>
              prev.map((t) => (t.id === id ? { ...t, pinned: !t.pinned } : t))
            )
          }
        />
      </ScrollArea>
    </ResizablePanel>,
    <ResizableHandle withHandle key="handle-left" />,
  ];

  const rightPanels = [
    <ResizableHandle withHandle key="handle-right" />,
    <ResizablePanel
      ref={rightRef}
      key="prompts"
      order={4}
      defaultSize={defaults.prompts}
      minSize={10}
      maxSize={26}
      collapsible
      collapsedSize={0}
      className="relative z-40 min-w-0 border-l border-border bg-background overflow-visible"
      style={{ overflow: isRightCollapsed ? "hidden" : "visible" }}
    >
      <SectionHeader
        title="Prompts"
        icon={<PanelRight className="h-4 w-4" />}
        edge="left"
        onToggle={
          !isRightCollapsed
            ? () => {
                rightRef.current?.collapse();
                setIsRightCollapsed(true);
              }
            : undefined
        }
        toggleIcon={<ChevronRight className="h-4 w-4" />}
      />
      <div className="p-2">
        <div className="mb-2 flex items-center gap-2 rounded-xl bg-muted/40 px-2 py-1.5">
          <Search className="h-4 w-4 text-muted-foreground" />
          <Input
            className="h-7 border-0 bg-transparent p-0 text-sm focus-visible:ring-0"
            placeholder="プロンプトを検索..."
          />
        </div>
      </div>
      <ScrollArea className="h-[calc(100%-44px-48px)] px-2 pb-2">
        <PromptList />
      </ScrollArea>
    </ResizablePanel>,
  ];

  return (
    <div className="flex h-dvh w-dvw overflow-hidden">
      <aside className="w-[56px] max-[1366px]:w-[48px] flex h-full flex-col items-center gap-2 border-r border-border bg-[#0f1720] text-white p-2">
        <TooltipProvider>
          <SidebarItem label="Home" icon={Home}>
            <DropdownMenuLabel>Home</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>New Chat</DropdownMenuItem>
            <DropdownMenuItem>Recent</DropdownMenuItem>
            <DropdownMenuItem>Favorites</DropdownMenuItem>
          </SidebarItem>

          <SidebarItem
            label="Chat"
            icon={MessageSquare}
            onPrimaryClick={() => {
              if (isLeftCollapsed) {
                leftRef.current?.expand();
                setIsLeftCollapsed(false);
              }
            }}
          >
            <DropdownMenuLabel>Chat</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>New Chat</DropdownMenuItem>
            <DropdownMenuItem>Archive</DropdownMenuItem>
            <DropdownMenuItem>Import</DropdownMenuItem>
          </SidebarItem>

          <SidebarItem
            label="Prompts"
            icon={Sparkles}
            onPrimaryClick={() => {
              if (isRightCollapsed) {
                rightRef.current?.expand();
                setIsRightCollapsed(false);
              }
            }}
          >
            <DropdownMenuLabel>Prompts</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>New Prompt</DropdownMenuItem>
            <DropdownMenuItem>Collections</DropdownMenuItem>
            <DropdownMenuItem>Gallery</DropdownMenuItem>
          </SidebarItem>

          <SidebarItem label="Files" icon={FileText}>
            <DropdownMenuLabel>Files</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Upload</DropdownMenuItem>
            <DropdownMenuItem>Browse</DropdownMenuItem>
            <DropdownMenuItem>Recent</DropdownMenuItem>
          </SidebarItem>

          <SidebarItem label="Settings" icon={Settings}>
            <DropdownMenuLabel>Settings</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>General</DropdownMenuItem>
            <DropdownMenuItem>Shortcuts</DropdownMenuItem>
            <DropdownMenuItem>Appearance</DropdownMenuItem>
          </SidebarItem>

          <SidebarItem label="Help" icon={HelpCircle}>
            <DropdownMenuLabel>Help</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Docs</DropdownMenuItem>
            <DropdownMenuItem>Keyboard Cheatsheet</DropdownMenuItem>
            <DropdownMenuItem>Report a bug</DropdownMenuItem>
          </SidebarItem>
        </TooltipProvider>
      </aside>

      <div ref={containerRef} className="relative h-full flex-1">
        <ResizablePanelGroup
          direction="horizontal"
          className="h-full min-w-0 overflow-visible"
        >
          {leftPanels}

          <ResizablePanel
            order={3}
            defaultSize={defaults.chat}
            minSize={40}
            className="bg-background"
          >
            {/* Chat area using shadcn ScrollArea */}
            <div className="flex h-full min-h-0 flex-col">
              <div className="flex-1 min-h-0">
                <ScrollArea className="h-full p-4" id="chat-scroll-area">
                  <MessageList />
                </ScrollArea>
              </div>

              <div className="border-t border-border bg-background p-2">
                <form
                  className="mx-auto flex max-w-3xl items-end gap-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                  }}
                >
                  <Textarea
                    placeholder="メッセージを入力..."
                    rows={2}
                    className="min-h-[44px] max-h-[180px] w-full resize-none"
                  />
                  <Button type="submit" size="sm">
                    送信
                  </Button>
                </form>
                <div className="h-[env(safe-area-inset-bottom)]" />
              </div>
            </div>
          </ResizablePanel>

          {rightPanels}
        </ResizablePanelGroup>

        {/* Overlay open-tabs so they are always visible when side panels are hidden */}
        {isLeftCollapsed && (
          <EdgeToggle
            side="left"
            onOpen={() => {
              leftRef.current?.expand();
              setIsLeftCollapsed(false);
            }}
          />
        )}
        {isRightCollapsed && (
          <EdgeToggle
            side="right"
            onOpen={() => {
              rightRef.current?.expand();
              setIsRightCollapsed(false);
            }}
          />
        )}
      </div>
    </div>
  );
}

function SectionHeader({
  title,
  icon,
  onToggle,
  toggleIcon,
  edge,
  extra,
}: {
  title: string;
  icon: React.ReactNode;
  onToggle?: (e: React.MouseEvent<HTMLButtonElement>) => void;
  toggleIcon?: React.ReactNode;
  edge?: "left" | "right";
  extra?: React.ReactNode;
}) {
  return (
    <div className="relative z-[80] flex h-11 items-center justify-between border-b border-border px-2">
      <div className="flex items-center gap-2 text-sm font-medium">
        {icon}
        <span>{title}</span>
      </div>
      <div className="flex items-center gap-1">{extra}</div>
      {onToggle ? (
        <div
          className={cn(
            "absolute top-1 z-[90] pointer-events-auto",
            edge === "right"
              ? "right-0 translate-x-[calc(100%+8px)]"
              : edge === "left"
              ? "left-0 -translate-x-[calc(100%+8px)]"
              : "right-2"
          )}
        >
          <ActionIcon tooltip="閉じる" onClick={(e) => onToggle(e)}>
            {toggleIcon ??
              (edge === "right" ? (
                <ChevronLeft className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              ))}
          </ActionIcon>
        </div>
      ) : null}
    </div>
  );
}

// Unified small round icon button used in headers
function ActionIcon({
  tooltip,
  onClick,
  children,
}: {
  tooltip?: string;
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  children: React.ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          onClick={onClick}
          className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-border bg-background/95 text-foreground shadow hover:bg-accent/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {children}
        </button>
      </TooltipTrigger>
      {tooltip ? (
        <TooltipContent side="top" sideOffset={6}>
          {tooltip}
        </TooltipContent>
      ) : null}
    </Tooltip>
  );
}

// Overlay tab to reopen collapsed side panels (left/right)
function EdgeToggle({
  side,
  onOpen,
}: {
  side: "left" | "right";
  onOpen: () => void;
}) {
  const isLeft = side === "left";
  const label = isLeft ? "スレッドを開く" : "プロンプトを開く";
  const style = isLeft ? { left: "8px" } : { right: "8px" };
  return (
    <div
      className={cn("absolute top-1 z-[95]")}
      style={style}
      aria-label={label}
      title={label}
    >
      <ActionIcon tooltip={label} onClick={onOpen}>
        {isLeft ? (
          <ChevronRight className="h-4 w-4" />
        ) : (
          <ChevronLeft className="h-4 w-4" />
        )}
      </ActionIcon>
    </div>
  );
}

function SidebarItem({
  label,
  icon: Icon,
  children,
  onPrimaryClick,
}: {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  onPrimaryClick?: () => void;
}) {
  return (
    <DropdownMenu>
      <Tooltip>
        <TooltipTrigger asChild>
          <DropdownMenuTrigger asChild>
            <button
              onClick={onPrimaryClick}
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-xl",
                "text-white hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40 transition"
              )}
              aria-label={label}
              title={label}
            >
              <Icon className="h-5 w-5" />
            </button>
          </DropdownMenuTrigger>
        </TooltipTrigger>
        <TooltipContent side="right" sideOffset={8}>
          {label}
        </TooltipContent>
      </Tooltip>
      <DropdownMenuContent
        side="right"
        align="start"
        sideOffset={10}
        collisionPadding={8}
        className="z-[200] w-44"
      >
        {children}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

type Thread = {
  id: string;
  title: string;
  last: string;
  updated: string;
  pinned?: boolean;
};

const INITIAL_THREADS: Thread[] = Array.from({ length: 24 }, (_, i) => ({
  id: `t-${i + 1}`,
  title:
    i % 5 === 0
      ? `🔥 Urgent: Model cost check #${i + 1}`
      : `Design sync / v${(i % 7) + 1}`,
  last: i % 3 === 0 ? "Let's ship it today." : "Refine system prompts & retry.",
  updated: `2025-09-${String((i % 28) + 1).padStart(2, "0")}`,
  pinned: i % 7 === 0, // 初期ピン留め
}));

function ThreadList({
  threads,
  selectedId,
  onSelect,
  onPinToggle,
  showPinIcon = false,
}: {
  threads: Thread[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onPinToggle: (id: string) => void;
  showPinIcon?: boolean;
}) {
  return (
    <div role="list" aria-label="スレッド" className="flex flex-col gap-1">
      {threads.map((t) => {
        const selected = selectedId === t.id;
        return (
          <div
            key={t.id}
            role="listitem"
            tabIndex={0}
            data-pinned={t.pinned ? "true" : "false"}
            onClick={() => onSelect(t.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect(t.id);
              }
            }}
            className={cn(
              "group grid grid-cols-[1fr_auto] items-center gap-2 h-9 w-full cursor-pointer select-none rounded-md px-2",
              selected
                ? "bg-accent/40 ring-1 ring-border"
                : "hover:bg-accent/30"
            )}
            aria-current={selected ? "true" : "false"}
          >
            <div className="min-w-0 flex items-center gap-1.5">
              {showPinIcon && t.pinned ? (
                <Pin
                  className="h-3.5 w-3.5 text-amber-500 shrink-0"
                  fill="currentColor"
                />
              ) : null}
              <span className="min-w-0 truncate text-sm font-medium">
                {t.title}
              </span>
            </div>

            {selected ? (
              <div className="shrink-0 justify-self-end">
                <DropdownMenu>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <DropdownMenuTrigger asChild>
                        <button
                          className={cn(
                            "inline-flex h-7 w-7 items-center justify-center rounded-md transition",
                            "opacity-100 hover:bg-accent/60"
                          )}
                          onClick={(e) => e.stopPropagation()}
                          aria-label="スレッド操作"
                          title="スレッド操作"
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </button>
                      </DropdownMenuTrigger>
                    </TooltipTrigger>
                    <TooltipContent side="top" sideOffset={6}>
                      操作
                    </TooltipContent>
                  </Tooltip>

                  <DropdownMenuContent
                    side="right"
                    align="start"
                    sideOffset={10}
                    collisionPadding={8}
                    className="z-[200] w-44"
                  >
                    <DropdownMenuItem
                      className="gap-2"
                      onClick={(e) => {
                        e.stopPropagation();
                        onPinToggle(t.id);
                      }}
                    >
                      <Pin className="h-4 w-4" />
                      {t.pinned ? "ピン留め解除" : "ピン留め"}
                    </DropdownMenuItem>
                    <DropdownMenuItem className="gap-2">
                      <Edit3 className="h-4 w-4" />
                      編集
                    </DropdownMenuItem>
                    <DropdownMenuItem className="gap-2">
                      <Copy className="h-4 w-4" />
                      複製
                    </DropdownMenuItem>
                    <DropdownMenuItem className="gap-2">
                      <Share2 className="h-4 w-4" />
                      共有
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem className="gap-2 text-destructive focus:text-destructive">
                      <Trash2 className="h-4 w-4" />
                      削除
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            ) : (
              <div className="shrink-0 justify-self-end w-7 h-7" aria-hidden />
            )}
          </div>
        );
      })}
    </div>
  );
}

// Pinned list (uses same ThreadList under the hood)
function PinnedList({
  threads,
  selectedId,
  onSelect,
  onPinToggle,
}: {
  threads: Thread[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onPinToggle: (id: string) => void;
}) {
  const pinned = threads.filter((t) => t.pinned);
  if (pinned.length === 0) {
    return (
      <div className="px-2 py-1 text-xs text-muted-foreground">
        ピン留めされたスレッドはありません
      </div>
    );
  }
  return (
    <ThreadList
      threads={pinned}
      selectedId={selectedId}
      onSelect={onSelect}
      onPinToggle={onPinToggle}
      showPinIcon
    />
  );
}

function FolderList() {
  const folders = [
    { id: "f-1", name: "プロダクト開発" },
    { id: "f-2", name: "会議草案案打ち" },
  ];
  return (
    <div className="flex flex-col gap-1">
      {folders.map((f) => (
        <div
          key={f.id}
          className="grid grid-cols-[1fr_auto] items-center h-9 gap-2 rounded-md px-2 hover:bg-accent/30"
        >
          <div className="flex items-center gap-2 min-w-0">
            <FolderClosed className="h-4 w-4 text-muted-foreground" />
            <span className="truncate text-sm font-medium">{f.name}</span>
          </div>
          <div className="shrink-0 justify-self-end">
            <DropdownMenu>
              <Tooltip>
                <TooltipTrigger asChild>
                  <DropdownMenuTrigger asChild>
                    <button
                      className="inline-flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent/60"
                      aria-label="フォルダ操作"
                      title="フォルダ操作"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </button>
                  </DropdownMenuTrigger>
                </TooltipTrigger>
                <TooltipContent side="top" sideOffset={6}>
                  操作
                </TooltipContent>
              </Tooltip>
              <DropdownMenuContent
                side="right"
                align="start"
                sideOffset={10}
                collisionPadding={8}
                className="z-[200] w-40"
              >
                <DropdownMenuItem className="gap-2">
                  <Edit3 className="h-4 w-4" />
                  編集
                </DropdownMenuItem>
                <DropdownMenuItem className="gap-2 text-destructive focus:text-destructive">
                  <Trash2 className="h-4 w-4" />
                  削除
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      ))}
    </div>
  );
}

const SAMPLE_PROMPTS = Array.from({ length: 28 }, (_, i) => ({
  id: `p-${i + 1}`,
  name:
    i % 4 === 0
      ? `Deep Research – Web v${(i % 3) + 1}`
      : `Bug triage template #${i + 1}`,
  desc:
    i % 2 === 0
      ? "Summarize, cite, and extract action items."
      : "Classify, label, and estimate severity.",
  tags: ["prod", i % 2 ? "eng" : "pm"],
}));

function PromptList() {
  return (
    <div className="flex flex-col gap-1">
      {SAMPLE_PROMPTS.map((p) => (
        <button
          key={p.id}
          className="group w-full rounded-lg border bg-card/50 p-2 text-left transition hover:bg-accent"
        >
          <div className="flex items-center justify-between">
            <span className="line-clamp-1 text-sm font-medium">{p.name}</span>
            <div className="flex shrink-0 gap-1">
              {p.tags.map((t) => (
                <span
                  key={t}
                  className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}

const SAMPLE_MESSAGES = Array.from({ length: 40 }, (_, i) => ({
  id: `m-${i + 1}`,
  role: i % 2 === 0 ? "assistant" : "user",
  text:
    i % 2 === 0
      ? `アシスタント：この案では中央カラムを優先し、左右は折りたたみ可能です（ケース #${
          i + 1
        }）。`
      : `ユーザー：なるほど。ではDPI 150%時も同じ操作感にしてください（ケース #${
          i + 1
        }）。`,
}));

function MessageList() {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-2">
      {SAMPLE_MESSAGES.map((m) => (
        <div
          key={m.id}
          className={cn(
            "flex w-full",
            m.role === "user" ? "justify-end" : "justify-start"
          )}
        >
          <div
            className={cn(
              "max-w-[85%] rounded-2xl px-3 py-2 text-sm",
              m.role === "user"
                ? "bg-primary text-primary-foreground rounded-br-sm"
                : "bg-muted text-foreground rounded-bl-sm"
            )}
          >
            {m.text}
          </div>
        </div>
      ))}
    </div>
  );
}
