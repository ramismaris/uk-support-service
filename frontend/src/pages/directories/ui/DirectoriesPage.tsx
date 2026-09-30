import { motion, useReducedMotion, type Variants } from 'framer-motion'
import { Building2, Tags } from 'lucide-react'
import { NavMenuButton } from '@/widgets/app-shell'
import { DirectoryCard } from './DirectoryCard'

const stagger: Variants = { shown: { transition: { staggerChildren: 0.06 } } }

export function DirectoriesPage() {
  const reduceMotion = useReducedMotion()
  return (
    <section className="flex min-w-0 flex-1 flex-col overflow-y-auto">
      <header className="border-b border-line px-3 py-3 lg:px-6">
        <div className="flex items-center gap-2">
          <NavMenuButton />
          <h1 className="text-lg font-semibold">Справочники</h1>
        </div>
      </header>
      <motion.div
        className="grid items-start gap-4 p-4 lg:p-6 xl:grid-cols-2"
        variants={stagger}
        initial={reduceMotion ? false : 'hidden'}
        animate="shown"
      >
        <DirectoryCard
          kind="buildings"
          title="Дома"
          icon={Building2}
          placeholder="Адрес дома"
          hint="Отключённый дом бот не предлагает, заявки и адреса жильцов остаются."
        />
        <DirectoryCard
          kind="categories"
          title="Категории заявок"
          icon={Tags}
          placeholder="🔧 Название категории"
          hint="Эмодзи — часть названия. Порядок здесь — порядок кнопок в боте."
        />
      </motion.div>
    </section>
  )
}
