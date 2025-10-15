"use client";

// ** State
import { useDemoStore } from "@/store/useDemoStore";

// ** Components(shadcn)
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";

// ** Icons
import { Minus, Plus } from "lucide-react";

// ** Types
interface SampleClientProps {
  dict: {
    integerSection: string;
    integerDescription: string;
    count: string;
    increment: string;
    decrement: string;
    reset: string;
    stringSection: string;
    stringDescription: string;
    textInput: string;
    currentText: string;
    clearText: string;
    objectSection: string;
    objectDescription: string;
    userName: string;
    userEmail: string;
    currentUser: string;
    resetForm: string;
    noData: string;
  };
}

// ** Function Component
const SampleClient = ({ dict }: SampleClientProps) => {
  const {
    count,
    increment,
    decrement,
    resetCount,
    text,
    setText,
    clearText,
    user,
    setUserName,
    setUserEmail,
    resetUser,
  } = useDemoStore();

  return (
    <div className="space-y-8">
      {/* Integer Section */}
      <div className="bg-card rounded-lg border border-border p-6 space-y-4">
        <div>
          <h2 className="text-2xl font-semibold">{dict.integerSection}</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {dict.integerDescription}
          </p>
        </div>
        <Separator />
        <div className="flex items-center gap-4">
          <span className="text-lg font-medium">{dict.count}:</span>
          <span className="text-3xl font-bold">{count}</span>
        </div>
        <div className="flex gap-2">
          <Button onClick={decrement} variant="outline" size="lg">
            <Minus className="h-4 w-4 mr-2" />
            {dict.decrement}
          </Button>
          <Button onClick={increment} size="lg">
            <Plus className="h-4 w-4 mr-2" />
            {dict.increment}
          </Button>
          <Button onClick={resetCount} variant="secondary" size="lg">
            {dict.reset}
          </Button>
        </div>
      </div>

      {/* String Section */}
      <div className="bg-card rounded-lg border border-border p-6 space-y-4">
        <div>
          <h2 className="text-2xl font-semibold">{dict.stringSection}</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {dict.stringDescription}
          </p>
        </div>
        <Separator />
        <div className="space-y-2">
          <Input
            placeholder={dict.textInput}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">{dict.currentText}:</span>
            <span className="text-sm text-muted-foreground">
              {text || dict.noData}
            </span>
          </div>
          <Button onClick={clearText} variant="outline">
            {dict.clearText}
          </Button>
        </div>
      </div>

      {/* Object Section */}
      <div className="bg-card rounded-lg border border-border p-6 space-y-4">
        <div>
          <h2 className="text-2xl font-semibold">{dict.objectSection}</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {dict.objectDescription}
          </p>
        </div>
        <Separator />
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">{dict.userName}</label>
            <Input
              value={user.name}
              onChange={(e) => setUserName(e.target.value)}
              placeholder="John Doe"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">{dict.userEmail}</label>
            <Input
              type="email"
              value={user.email}
              onChange={(e) => setUserEmail(e.target.value)}
              placeholder="john@example.com"
            />
          </div>
          <div className="bg-muted rounded-lg p-4 space-y-2">
            <p className="text-sm font-semibold">{dict.currentUser}:</p>
            <p className="text-sm">
              {dict.userName}:{" "}
              <span className="text-muted-foreground">
                {user.name || dict.noData}
              </span>
            </p>
            <p className="text-sm">
              {dict.userEmail}:{" "}
              <span className="text-muted-foreground">
                {user.email || dict.noData}
              </span>
            </p>
          </div>
          <Button onClick={resetUser} variant="outline">
            {dict.resetForm}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default SampleClient;
