"use client";

import { motion } from "motion/react";
import { Button } from "@/components/ui/button";
import { MessageSquare, Sparkles, Zap } from "lucide-react";
import Link from "next/link";

interface HomeClientProps {
  dict: {
    title: string;
    subtitle: string;
    description: string;
    ctaPrimary: string;
    ctaSecondary: string;
    features: {
      title: string;
      safety: { title: string; description: string };
      culture: { title: string; description: string };
      learning: { title: string; description: string };
    };
    stats: {
      developers: string;
      projects: string;
      satisfaction: string;
    };
  };
  lang: string;
}

const HomeClient = ({ dict, lang }: HomeClientProps) => {
  const features = [
    {
      icon: Sparkles,
      title: dict.features.safety.title,
      description: dict.features.safety.description,
    },
    {
      icon: MessageSquare,
      title: dict.features.culture.title,
      description: dict.features.culture.description,
    },
    {
      icon: Zap,
      title: dict.features.learning.title,
      description: dict.features.learning.description,
    },
  ];

  const stats = [
    { value: "10,000+", label: dict.stats.developers },
    { value: "50,000+", label: dict.stats.projects },
    { value: "98%", label: dict.stats.satisfaction },
  ];

  return (
    <div className="min-h-screen">
      <section className="container mx-auto px-4 py-20 md:py-32">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight">
              {dict.title}
            </h1>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <p className="text-xl md:text-2xl text-muted-foreground">
              {dict.subtitle}
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <p className="text-base md:text-lg text-muted-foreground max-w-2xl mx-auto">
              {dict.description}
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex flex-col sm:flex-row gap-4 justify-center"
          >
            <Button asChild size="lg" className="text-base">
              <Link href={`/${lang}/chat`}>{dict.ctaPrimary}</Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="text-base">
              <Link href={`/${lang}/sample`}>{dict.ctaSecondary}</Link>
            </Button>
          </motion.div>
        </div>
      </section>

      <section className="container mx-auto px-4 py-20">
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-bold">
            {dict.features.title}
          </h2>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={{
            hidden: { opacity: 0 },
            visible: {
              opacity: 1,
              transition: { staggerChildren: 0.2 },
            },
          }}
          className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto"
        >
          {features.map((feature, index) => (
            <motion.div
              key={index}
              variants={{
                hidden: { opacity: 0, y: 30 },
                visible: { opacity: 1, y: 0 },
              }}
              className="bg-card rounded-lg border border-border p-6 space-y-4"
            >
              <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                <feature.icon className="h-6 w-6 text-primary" />
              </div>
              <h3 className="text-xl font-semibold">{feature.title}</h3>
              <p className="text-muted-foreground">{feature.description}</p>
            </motion.div>
          ))}
        </motion.div>
      </section>

      <section className="container mx-auto px-4 py-20">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={{
            hidden: { opacity: 0 },
            visible: {
              opacity: 1,
              transition: { staggerChildren: 0.15 },
            },
          }}
          className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto text-center"
        >
          {stats.map((stat, index) => (
            <motion.div
              key={index}
              variants={{
                hidden: { opacity: 0, scale: 0.8 },
                visible: { opacity: 1, scale: 1 },
              }}
              className="space-y-2"
            >
              <div className="text-4xl md:text-5xl font-bold text-primary">
                {stat.value}
              </div>
              <div className="text-muted-foreground">{stat.label}</div>
            </motion.div>
          ))}
        </motion.div>
      </section>
    </div>
  );
};

export default HomeClient;
