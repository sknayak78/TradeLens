declare module "@/components/ui/accordion" {
  import * as React from "react";

  export const Accordion: React.FC<React.ComponentProps<"div"> & {
    type?: "single" | "multiple";
    defaultValue?: string | string[];
    collapsible?: boolean;
  }>;
  export const AccordionItem: React.FC<React.ComponentProps<"div"> & { value: string }>;
  export const AccordionTrigger: React.FC<React.ComponentProps<"button">>;
  export const AccordionContent: React.FC<React.ComponentProps<"div">>;
}
