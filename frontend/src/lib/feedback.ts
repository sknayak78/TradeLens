import { toast } from "@/hooks/use-toast";
import { toApiError } from "@/services/api";

export function showSuccess(message: string, description?: string) {
  toast({
    title: message,
    description,
  });
}

export function showError(message: string, description?: string) {
  toast({
    title: message,
    description,
    variant: "destructive",
  });
}

export function showApiError(context: string, err: unknown) {
  const { message } = toApiError(err);
  showError(context, message);
}
