"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

const feedbackSchema = z.object({
  feedback: z
    .string()
    .min(10, "Feedback must be at least 10 characters")
    .max(1000, "Feedback must be less than 1000 characters"),
});

type FeedbackFormValues = z.infer<typeof feedbackSchema>;

interface FeedbackDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function FeedbackDialog({
  open,
  onOpenChange,
}: FeedbackDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  const form = useForm<FeedbackFormValues>({
    resolver: zodResolver(feedbackSchema),
    defaultValues: {
      feedback: "",
    },
  });

  const onSubmit = async (data: FeedbackFormValues) => {
    setIsSubmitting(true);
    try {
      const response = await fetch("/api/feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ feedback: data.feedback }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to submit feedback");
      }

      setSubmitSuccess(true);
      form.reset();

      // Close dialog after 2 seconds
      setTimeout(() => {
        setSubmitSuccess(false);
        onOpenChange(false);
      }, 2000);
    } catch (error) {
      console.error("Error submitting feedback:", error);
      form.setError("feedback", {
        type: "manual",
        message:
          error instanceof Error
            ? error.message
            : "Failed to submit feedback. Please try again.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-125 bg-surface-raised border-border-muted data-[state=open]:slide-in-from-left-0! data-[state=open]:slide-in-from-top-0! data-[state=closed]:slide-out-to-left-0! data-[state=closed]:slide-out-to-top-0!">
        <DialogHeader>
          <DialogTitle>Leave Feedback</DialogTitle>
          <DialogDescription className="text-secondary">
            We&apos;d love to hear your thoughts, suggestions, or report any
            issues.
          </DialogDescription>
        </DialogHeader>
        {submitSuccess ? (
          <div className="py-8 text-center">
            <p className="text-green-400 font-medium">
              Thank you for your feedback!
            </p>
          </div>
        ) : (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="feedback"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-primary">Description</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Share your feedback here..."
                        className="min-h-30 resize-none bg-transparent"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                  disabled={isSubmitting}
                  className="bg-surface-raised border-border-muted text-zinc-300 hover:bg-surface-hover hover:text-zinc-300"
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Submitting..." : "Submit Feedback"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        )}
      </DialogContent>
    </Dialog>
  );
}
