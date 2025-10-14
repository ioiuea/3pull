import { getDictionary, type Locale } from '@/utils/dictionaries'
import { SampleClient } from '@/components/sample'

export default async function ZustandDemoPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  const dict = await getDictionary(lang as Locale);
  
  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="max-w-4xl w-full space-y-8">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold">
            {dict.sample.title}
          </h1>
          <p className="text-xl text-foreground/70">
            {dict.sample.description}
          </p>
        </div>
        
        <SampleClient dict={dict.sample} />
      </div>
    </div>
  )
}
