interface Props {
  phase: string;
  title: string;
  items: string[];
}

export default function ComingSoon({ phase, title, items }: Props) {
  return (
    <section className="coming-soon panel">
      <span className="badge">{phase}</span>
      <h2>{title}</h2>
      <p className="dim">Este módulo se construye en una fase posterior del plan. Incluirá:</p>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
